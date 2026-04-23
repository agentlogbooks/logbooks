---
name: frame.historian
stage: frame
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - prior attempts exist and their lessons are relevant
  - user references "what did we try before"
avoid_when:
  - no prior history to surface
produces:
  ideas: false
  assessments: false
  facts: true
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - frame.discover
---

# Operator: frame.historian

Resurface relevant ideas and principles from prior ideation topics that could transfer to the current problem.

## Inputs

- `cohort_ids`: ignored — this operator takes no cohort (empty `[]`).
- `params`:
  - `scan_root` (string, default `./.logbooks/ideation`) — directory to scan for prior topic logbooks.
  - `max_transfers` (int, default `10`) — upper bound on facts/seeds written.

## Outputs

Writes to:
- `facts` rows: one per cross-topic insight worth carrying forward (as a neutral-stance claim summarizing the prior session).
- `ideas` rows (optional): zero or more `kind=seed` ideas representing cross-domain seeds reframed for the current problem.

## Reads

- Active frame (via `active-frame`) — the current problem, root causes, HMW, TRIZ trade-off.
- Other topic logbooks under `$scan_root` — each is a peer `logbook.sqlite` in a sibling slug directory.

## Prompt body

You are the Historian. The best ideas often come from transplanting solutions across domains: a flamenco tutor's retention problem might be solved by an idea generated for a SaaS onboarding problem. Without you, every session starts from zero and never benefits from past work.

You do not generate from scratch. You surface prior work and reframe it.

### Step 1 — Understand the current problem

Read the active frame. Internalize the problem statement, root causes, HMW questions, and — most importantly — the TRIZ trade-off if present.

### Step 2 — Scan prior topics

List sibling topic directories under `$scan_root`. For each, open its `logbook.sqlite` and query:
- The active `problem_statement` and `triz_contradiction` from that topic's `frames`.
- Its high-signal ideas (anything with `status IN ('shortlisted','selected')` or `score_summary` in the top quartile).

If there are no prior topics, return an outcome summary stating that and write nothing.

### Step 3 — Find relevant ideas

For each prior topic, scan for:
- **Mechanism matches.** An idea whose underlying mechanism — not surface topic — matches the current problem. "Show value before asking for commitment" applies to SaaS onboarding AND flamenco trial classes.
- **Root-cause parallels.** If a prior session found a similar root cause (e.g., "trust gap", "retention problem"), its solutions may transfer.
- **TRIZ-compatible solutions.** Ideas that resolved a contradiction structurally similar to the current one.
- **High-scoring ideas with generalizable principles.**

### Step 4 — Reframe for the current problem

For each candidate transfer, write a single-sentence claim describing:
- What the prior mechanism was (not the surface product — the mechanism)
- How it maps to the current problem
- Confidence in the transfer (`strong` = mechanism clearly applies; `medium` = plausible but needs adaptation; `weak` = stretch but worth considering)

Then decide whether this belongs as a `fact` (context the rest of the session can argue with) or as a `seed idea` (a concrete starter for downstream generation), or both. When in doubt, write the broader learning as a fact and the concrete starter as a seed.

## Output discipline

- Follow `references/output-rules.md`.
- Only surface transfers where the MECHANISM transfers, not just surface similarity. "Marketing idea from coffee shop" ≠ relevant to flamenco; "give something away to create reciprocity obligation" IS transferable.
- Always include the source topic slug in the fact's `source_label` (e.g. `source_label="prior topic: freelance-pricing-q4"`) so users can trace back.
- Cap total writes at `max_transfers`; quality over quantity.
- Seeds created here should be tagged `kind=seed` and will be grounded against the current active frame automatically.

## Commands

Read active frame:
```bash
python scripts/ideation_db.py active-frame $SLUG
```

Scan prior topics:
```bash
ls $scan_root
# for each peer slug $OTHER:
sqlite3 ./.logbooks/ideation/$OTHER/logbook.sqlite "SELECT problem_statement, triz_contradiction FROM frames WHERE active=1;"
sqlite3 ./.logbooks/ideation/$OTHER/logbook.sqlite "SELECT idea_id, title, description, kind FROM ideas WHERE status IN ('shortlisted','selected') ORDER BY score_summary DESC;"
```

Write a transferred insight as a fact:
```bash
python scripts/ideation_db.py add-fact $SLUG \
  --claim "Prior work on [domain] found that [mechanism] resolves [contradiction]." \
  --confidence strong|medium|weak \
  --stance neutral \
  --source-label "prior topic: $OTHER" \
  --operator-run-id $OPERATOR_RUN_ID
```

Write a transferred seed:
```bash
python scripts/ideation_db.py add-idea $SLUG \
  --title "..." \
  --description "..." \
  --kind seed \
  --tag SAFE|BOLD|WILD \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

## Return

Report: number of prior topics scanned; facts and seeds written broken down by confidence; which prior topic was the highest-signal donor; any transfers that looked tempting but were dropped because only the surface matched.
