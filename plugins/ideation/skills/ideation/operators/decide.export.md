---
name: decide.export
stage: decide
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - pool has selected ideas ready to leave the skill
  - user asks for "menu" or "export"
avoid_when:
  - nothing selected yet
produces:
  ideas: false
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups: []
---

# Operator: decide.export

Produce a portable final artifact (markdown) for sharing outside the logbook. Supports three formats: `menu`, `narrative`, `table`. The `menu` format additionally writes `menu_bucket` assessments that assign each shortlisted/selected idea to Quick Wins / Core Bets / Moonshots.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to include in the export. Typically all `status IN ('shortlisted','selected')` ideas. Must be non-empty.
- `params`:
  - `format` (string, required) — one of `menu`, `narrative`, `table`.
  - `title` (string, optional) — title to put at the top of the report. Defaults to the active frame's `problem_statement`.

## Outputs

- **External file:** `./.logbooks/ideation/$SLUG/reports/$RUN_ID-<format>.md`.
- For `format=menu` only: one `assessments` row per bucketed idea, `metric=menu_bucket`, `value` one of `quick_win|core_bet|moonshot`, `rationale` = one sentence naming the bucket criterion (see buckets below). Most ideas receive no bucket — 3-5 per bucket maximum.
- No other logbook mutations.

## Reads

- Active frame via `active-frame` (for the title and problem statement).
- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID`.
- Latest assessments for: `feasibility`, `novelty`, `brilliance.tier`, `web_stress_verdict`, `converge_reason`, `taste` — via `ideation_db.py latest-assessment`.

## Prompt body

This is an export, not a decision. Do NOT change statuses; do NOT invent new content. You pull what's in the logbook and shape it for a human reader outside the session.

### Format `table`

Simple flat markdown table with columns: `#`, `Title`, `Kind`, `Status`, `Evidence state`, `Why it's here` (short phrase). Sort by `score_summary DESC` with NULLs last. One row per idea. Below the table, the full `description` for each idea in order.

### Format `narrative`

Prose summary, not a table. Structure:

1. **Context** — 2-3 sentences paraphrasing the active frame's problem statement and deepest root cause.
2. **What the session produced** — one sentence per selected idea, naming the mechanism and its impact. No IDs in prose; IDs appear as parentheticals.
3. **What's still open** — 2-3 sentences naming the strongest surviving objection across the selected set, drawn from `web_stress_verdict` rationales. If adversarial facts exist, cite one specifically as a documented case (not a category claim).
4. **Shortlisted but not selected** — one sentence per shortlisted-only idea, explaining why it's still worth reconsidering.

### Format `menu`

Group ideas into three qualitative buckets. Bucket assignment is a JUDGMENT based on the idea's profile in the logbook — no numeric thresholds. Most ideas stay unbucketed; aim for 3-5 per bucket maximum.

| Bucket | Qualitative definition | Signals |
|---|---|---|
| **Quick Wins** | Can start immediately with existing resources; low structural risk; delivers value fast. | High `feasibility`; clear first step; no new capability needed. |
| **Core Bets** | Main strategic plays addressing the session's deepest root cause. | Directly resolves the active frame's root cause or a tension. `brilliance.tier='brilliant'` is a strong signal here. |
| **Moonshots** | High-novelty, high-upside; needs proof search before commitment. | High `novelty`; structurally surprising; upside justifies the unknowns. `evidence_state='untested'` is typical. |

For `format=menu`, collect every bucketed idea into one tempfile and write them in a single `add-assessments-batch` call (see Commands below). Most ideas stay unbucketed — the batch holds only the 3-5 per bucket you assign.

Then render the report as:

```markdown
# <title>

## Quick Wins
> Can be started immediately with existing resources; low structural risk.

### Idea #12 — <title>
<description>
Why quick: <one sentence from rationale>

## Core Bets
> Main strategic plays addressing the session's deepest root cause.

### Idea #34 — <title>
<description>
Why it's a bet: <one sentence>

## Moonshots
> High-novelty, high-upside; validate before committing.

### Idea #58 — <title>
<description>
What to check first: <one sentence, drawn from web_stress strongest objection or open question>
```

## Output discipline

- Follow `references/output-rules.md`. No raw scores, no weights, no methodology names anywhere in the report.
- CRITICAL: the report must NOT include "6-week MVP", "Week 1 / Week 2", "ship in Q2", "90-day metrics", or invented timelines. These estimates are fabrications — the agent has no knowledge of team, scope, or prior work.
- Bucket assignment is sparse — most ideas remain unbucketed. Assigning every idea to a bucket defeats the signal.
- The table format is the least prose-heavy — use it when the user wants to paste into an issue tracker.
- File path is `./.logbooks/ideation/$SLUG/reports/$RUN_ID-<format>.md`. Overwrite if exists.

## Commands

**Batch every write.** For `format=menu` with K bucketed ideas, this operator should produce exactly 1 write subprocess call (one `add-assessments-batch` for all `menu_bucket` rows) plus the report file. For `format=table` or `format=narrative`, zero write subprocess calls — only the report file. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read context (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py idea $SLUG $IDEA_ID
python scripts/ideation_db.py latest-assessment $SLUG --idea-id $IDEA_ID --metric brilliance.tier

# For format=menu, write ALL menu_bucket assessments in ONE call BEFORE rendering the report.
cat > /tmp/export-menu-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "menu_bucket", "value": "quick_win",
   "rationale": "High feasibility, one clear first step, existing tech stack supports it."},
  {"idea_id": 34, "metric": "menu_bucket", "value": "core_bet",
   "rationale": "Directly resolves the active frame's root cause; brilliant tier backs it."},
  {"idea_id": 58, "metric": "menu_bucket", "value": "moonshot",
   "rationale": "High novelty, evidence_state=untested — worth a proof search before commitment."}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/export-menu-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/export-menu-$OPERATOR_RUN_ID.json

# Ensure reports dir and write the report
mkdir -p "./.logbooks/ideation/$SLUG/reports"
# Path: ./.logbooks/ideation/$SLUG/reports/$RUN_ID-<format>.md
```

**Do not** call `add-assessment` per bucketed idea. The batch form is strictly faster and preserves transactional atomicity.

## Return

A 1-3 sentence outcome summary: format used, count of ideas included, (menu only) bucket distribution with bucketed IDs, and the absolute path of the report file written.
