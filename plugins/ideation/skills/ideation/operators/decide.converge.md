---
name: decide.converge
stage: decide
scope: pool
applies_to:
  kinds: []
  min_cohort: 2
use_when:
  - pool has been evaluated and validated
  - user asks to "pick" or "decide" or "converge"
avoid_when:
  - evaluation incomplete (no scores)
produces:
  ideas: false
  assessments: true
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - decide.export
---

# Operator: decide.converge

Final-decision ceremony. Presents the shortlisted cohort to the user with all assessment context, spawns `AskUserQuestion` to let them choose which ideas become `status='selected'`, patches statuses accordingly, and writes a converge report capturing the rationale.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to present. Typically all `status='shortlisted'` ideas. Must be 2-8; below 2 there's nothing to converge, above 8 the decision tree is too noisy.
- `params`:
  - `max_selected` (int, default 3) — hard cap on how many ideas can become `status='selected'` in one converge run.
  - `decision_tree` (bool, default true) — if true, run a short filter question (time horizon / authority / risk appetite) before the final pick, to help the user see fit.

## Outputs

- `ideas` mutable-field patches:
  - Selected ideas → `status='selected'`.
  - Ideas explicitly declined by the user in this converge run → `status='rejected'`.
  - Shortlisted ideas the user neither picked nor rejected stay `status='shortlisted'` (the user may revisit).
- `assessments` rows: one per selected idea, `metric=converge_reason`, `value` = short label (e.g. `user_selected`, `strong_evidence`, `brilliant_and_validated`), `rationale` = the user's stated reason or a paraphrase.
- **External file:** `./.ideation/$SLUG/reports/$RUN_ID-converge.md` — captures the decision tree, the shortlist with evidence, the user's choices, and the reasoning.

## Reads

- Active frame via `active-frame` (to show the user what problem they framed).
- Every cohort idea via `ideation_db.py idea $SLUG $IDEA_ID`.
- Latest assessments per idea across key metrics (taste, web_stress_verdict, brilliance.tier, shortlist_reason).
- Adversarial facts via `ideation_db.py facts $SLUG --stance adversarial` — must cite at least one in the report if any exist.

## Prompt body

This is the last step where the user sets direction for follow-up. Do not inflate. Do not invent timelines. Let the user decide.

**Step 1 — Decision tree (if `decision_tree=true`).** Spawn `AskUserQuestion` with 2-4 options covering time horizon / authority / risk appetite:

```
AskUserQuestion:
  question: "You have N shortlisted ideas. A quick filter to find the best fit:
    - Time horizon: when do you need to see results?
    - Authority: what can you act on unilaterally?
    - Risk appetite: safety / balanced / upside?"
  header: "Filter"
  options:
    - "Fast results (< 2 weeks), unilateral, safety-oriented"
    - "Medium term (1-3 months), some approval, balanced"
    - "Long game (3+ months), need buy-in, high upside"
    - "I'll pick directly — skip the filter"
```

Use the user's choice to reorder the shortlist by fit (don't filter out ideas — just reorder).

**Step 2 — Present the shortlist with evidence.** Spawn a second `AskUserQuestion` with one option per shortlisted idea (batches of 4 if needed). Each option is `"Idea #NN: <title>"` plus a one-sentence reason the idea is on the shortlist. Include an "I need to think — save all, select none" option and a "None of these — reject all" option.

If adversarial facts exist in the logbook, the question text must cite at least one: `"Note: fact #7 says [adversarial claim] (source). Consider this when picking."`

Allow multiple rounds if more than 4 options. Collect up to `max_selected` picks.

**Step 3 — Patch statuses.**
- Each picked idea → `status='selected'`.
- Each idea the user explicitly rejected in the flow → `status='rejected'`.
- Ideas not touched in this converge run stay `shortlisted`.

**Step 4 — Write `converge_reason` assessments** on each selected idea. The `rationale` quotes or paraphrases the user's reason ("User picked because the evidence on competitor pricing matched their own data.").

**Step 5 — Write the converge report** to `./.ideation/$SLUG/reports/$RUN_ID-converge.md`:

```markdown
# Converge — run $RUN_ID

## Problem statement (active frame)
<from active-frame>

## Decision filter
<user's answer, or "skipped">

## Shortlist presented
| # | Title | Reason on shortlist | Evidence state |
|---|---|---|---|
| 12 | ... | ... | supported |

## Selected
### Idea #12 — <title>
<description>
User's reason: <quote or paraphrase>
Strongest surviving objection to monitor: <from web_stress_verdict rationale, if any>

## Rejected
### Idea #47 — <title>
User declined because: <their reason>

## Parked (still shortlisted)
<ideas not touched this run>
```

## Output discipline

- Follow `references/output-rules.md`. CRITICAL for converge output: do NOT include implementation timeline estimates, "6-week MVP", "Week 1 / Week 2", "90-day success metrics", or first-action checklists. The agent does not know the user's team, stack, prior work, or scope.
- Focus instead on: each selected idea's mechanism, why it fits the problem (active frame), and what assumptions still need validating (from web-stress strongest objection).
- When citing adversarial facts, present each as ONE specific documented case — never as proof a category of idea won't work. Say "this one competitor failed for reason X" not "ideas of this type don't work."
- No raw scores. No methodology names. No bucket names unless the user sees them in context.

## Commands

**Batch every write.** After all `AskUserQuestion` rounds, this operator should produce exactly 2 write subprocess calls total — one `patch-ideas-batch` (every `status='selected'` or `status='rejected'` patch) and one `add-assessments-batch` (all `converge_reason` rows for selected ideas) — plus the report file. No matter how many ideas are selected or rejected. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read context (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py idea $SLUG $IDEA_ID
python scripts/ideation_db.py facts $SLUG --stance adversarial

# Run AskUserQuestion flows (decision tree + selection). See prompt body.
# Collect ALL user decisions first, then batch them.

# Patch selected + rejected statuses in ONE call.
cat > /tmp/converge-patch-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "column": "status", "value": "selected"},
  {"idea_id": 34, "column": "status", "value": "selected"},
  {"idea_id": 47, "column": "status", "value": "rejected"},
  {"idea_id": 58, "column": "status", "value": "rejected"}
]
JSON

python scripts/ideation_db.py patch-ideas-batch $SLUG /tmp/converge-patch-$OPERATOR_RUN_ID.json

rm -f /tmp/converge-patch-$OPERATOR_RUN_ID.json

# Record converge_reason for every selected idea in ONE call.
cat > /tmp/converge-reasons-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "converge_reason", "value": "user_selected",
   "rationale": "User chose this because the competitor pricing evidence matched their own data and the one-mechanism insight was clear."},
  {"idea_id": 34, "metric": "converge_reason", "value": "brilliant_and_validated",
   "rationale": "User chose this because it resolves the session's deepest tension and survived web-stress."}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/converge-reasons-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/converge-reasons-$OPERATOR_RUN_ID.json

# Write the report file
mkdir -p "./.ideation/$SLUG/reports"
# Path: ./.ideation/$SLUG/reports/$RUN_ID-converge.md
```

**Do not** call `patch-idea` or `add-assessment` per idea. The batch form is strictly faster and preserves transactional atomicity — either the whole converge lands or none of it does.

## Return

A 1-3 sentence outcome summary: which idea IDs are now `selected`, which are `rejected`, which remain `shortlisted`, and the path of the converge report file.
