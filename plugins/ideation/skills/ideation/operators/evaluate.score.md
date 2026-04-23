---
name: evaluate.score
stage: evaluate
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - criteria are locked and ideas need composite scores
  - user wants ranking before converge
avoid_when:
  - no criteria yet (run evaluate.criteria first)
produces:
  ideas: false
  assessments: true
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - decide.shortlist
  - decide.compare
---

# Operator: evaluate.score

Apply a previously-derived criteria set to every idea in the cohort, write one assessment per (idea, criterion), compute a weighted composite, and patch `ideas.score_summary`. Does NOT invent criteria — consumes the JSON file produced by `evaluate.criteria`.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to score. Typically the full active cohort (seed + variant + hybrid + refinement + counter ideas).
- `params`:
  - `criteria_path` (string, required) — absolute path to a `criteria-$RUN_ID.json` file produced by an earlier `evaluate.criteria` run.
  - `min_cohort` (int, default 20) — if the cohort is smaller, proceed but note the thin sample in the outcome summary.

## Outputs

- `assessments` rows: for each idea × each criterion, one row with `metric=<criterion_name>`, `value` = integer string `"1"`..`"5"`, `value_numeric` = the same integer as a REAL, `rationale` = a one-sentence justification, and `evidence_fact_ids` populated when a specific `facts` row backs the score.
- `ideas` mutable-field patches: `score_summary = composite` (REAL) for each scored idea.
- No external files.

## Reads

- `criteria_path` — the JSON file of criteria and weights. This is authoritative; do not change either.
- Active frame via `active-frame` (context for root-cause-linked criteria).
- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID`.
- Relevant facts via `ideation_db.py facts $SLUG` when a fact directly supports or contradicts a specific criterion judgment.

## Prompt body

You rank ideas you did not generate. You apply exactly the criteria in `criteria_path` — you do NOT redefine them and you do NOT change weights.

**Step 1 — Load criteria.** Read `criteria_path`. Verify `total_weight == 100` and each `criterion.name` matches `^[a-z][a-z0-9_]*$`. If the file is malformed, fail the run; the orchestrator must re-run `evaluate.criteria`.

**Step 2 — Score every cohort idea on every criterion.** Each score is an integer 1-5 where:
- 1: criterion is barely met
- 2: partially meets it
- 3: meets it adequately
- 4: clearly meets it
- 5: exceptional on this axis

**Forced distribution rule (per criterion, across the full cohort):** at least one idea must receive a 1 and at least one must receive a 5. Without this, scores collapse to a narrow middle and ranking fails to discriminate. If no idea truly deserves a 5, give the best available a 5 and name the concession in `rationale`.

**Step 3 — Evidence.** Every score needs a `rationale` that names what justifies it. Where a specific `facts` row supports or contradicts the score, list its `fact_id` in `evidence_fact_ids`. Scores with no justification are fabricated — they block the composite.

**Step 4 — Composite.** For each idea, compute weighted average:
  `composite = sum(score_i * weight_i) / 100`
Patch `ideas.score_summary = composite`. Round to 2 decimals for storage.

**What you do NOT do:**
- Generate new ideas.
- Redefine criteria or weights.
- Invent numeric precision (market size, revenue, effort days) — your scores are honest 1-5 subjective judgments, not fake objectivity.
- Mutate `evidence_state` — that belongs to validate operators.

## Output discipline

- Follow `references/output-rules.md`. `rationale` stays coffee-talk (no formulas, no methodology names). `value` is the bare integer.
- `value_numeric` must equal the integer in `value` to 1e-6 tolerance (db validation).
- One assessment per (idea, criterion) per run. If the same (idea, criterion) is re-scored in a later run, that's a new row — never update prior rows.
- Patch `score_summary` exactly once per idea after all criterion assessments for that idea are written.

## Commands

**Write all assessments and composite patches in BULK.** For a cohort of N ideas and K criteria, the per-row CLI would spawn N×K + N subprocess calls — hundreds of spawns for a full cohort. Always use the batch endpoints below: two CLI calls total (one for assessments, one for score_summary patches), regardless of cohort size.

```bash
# Load criteria
cat "$CRITERIA_PATH"

# Read context (one call per idea is fine — reads are cheap)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py ideas $SLUG --status active
python scripts/ideation_db.py facts $SLUG

# Build one JSON file holding every (idea, criterion) assessment for the cohort.
# Write it to a tempfile you control — e.g. /tmp/score-$OPERATOR_RUN_ID.json.
cat > /tmp/score-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "feasibility", "value": "4", "value_numeric": 4,
   "rationale": "Existing payment rails cover 80% of the integration; remaining work is a two-week sprint.",
   "evidence_fact_ids": [7]},
  {"idea_id": 12, "metric": "novelty", "value": "3", "value_numeric": 3,
   "rationale": "Similar pricing models exist; the pairing with the usage signal is the new piece."},
  {"idea_id": 13, "metric": "feasibility", "value": "2", "value_numeric": 2,
   "rationale": "Requires a vendor partnership we don't have."},
  ...
]
JSON

# ONE call writes all N×K assessment rows.
python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/score-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

# Compute each idea's composite locally (sum of score_i * weight_i / 100) while
# you build the JSON above — you already have the numbers. Then ONE call patches
# every score_summary:
cat > /tmp/score-patch-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "column": "score_summary", "value": 3.75},
  {"idea_id": 13, "column": "score_summary", "value": 2.10},
  ...
]
JSON

python scripts/ideation_db.py patch-ideas-batch $SLUG /tmp/score-patch-$OPERATOR_RUN_ID.json

# Clean up tempfiles.
rm -f /tmp/score-$OPERATOR_RUN_ID.json /tmp/score-patch-$OPERATOR_RUN_ID.json
```

**Do not** call `add-assessment` or `patch-idea` one-at-a-time in a loop. The batch form is strictly faster and preserves transactional atomicity — either every score lands or none do.

## Return

A 1-3 sentence outcome summary: cohort size scored, composite distribution (min / median / max), any criteria where forced-distribution required a concession, and any ideas skipped (with reason).
