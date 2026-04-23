---
name: decide.compare
stage: decide
scope: pool
applies_to:
  kinds: []
  min_cohort: 2
use_when:
  - user wants side-by-side readout of a cohort
  - after generate or transform bursts
avoid_when:
  - single idea (no comparison possible)
produces:
  ideas: false
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - decide.shortlist
  - decide.converge
---

# Operator: decide.compare

Render a side-by-side comparison report of the cohort for human review. One row per idea; columns show title, a short description, key latest assessments, and current `evidence_state`. Output is a markdown file — not a logbook row.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to compare. Typically the output of `decide.shortlist` (ideas at `status='shortlisted'`) or a user-specified set.
- `params`:
  - `metrics` (list of strings, optional) — which `assessments.metric` values to include as columns. If omitted, defaults to: `feasibility`, `novelty`, `web_stress_verdict`, `brilliance.tier`, `taste`. The operator includes all criteria columns from the criteria JSON if available.
  - `criteria_path` (string, optional) — path to `criteria-$RUN_ID.json` whose criteria should appear as columns.

## Outputs

- **External file:** `./.logbooks/ideation/$SLUG/reports/$RUN_ID-compare.md` — a markdown report containing:
  - One-line header naming the cohort + run ID.
  - A table with columns: `#`, `Title`, `Kind`, `Evidence state`, `Status`, plus one column per metric in `params.metrics`.
  - Below the table, one paragraph per idea with the full `description` plus the latest-assessment rationales that matter most (taste, brilliance pitch, web-stress strongest objection).
- No logbook rows are written. No patches.

## Reads

- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID`.
- Latest assessment per metric per idea via `ideation_db.py latest-assessment $SLUG --idea-id $ID --metric $METRIC`.
- `criteria_path` if passed — so the criteria are displayed as column headers verbatim.

## Prompt body

**Step 1 — Read the cohort.** Pull every idea in `cohort_ids` with all immutable + mutable fields.

**Step 2 — Decide on columns.** If `params.metrics` is passed, use it. Otherwise default to: each `criteria_path` criterion (if present), then `web_stress_verdict`, `brilliance.tier`, `taste`. Cap at 8 metric columns — more makes the table unreadable.

**Step 3 — Read latest assessments.** For each (idea, metric) pair, read the latest row via `latest-assessment`. Empty cells are OK — render as `—`.

**Step 4 — Build the table.**
- `Kind` column uses the stored value (`seed`, `variant`, `hybrid`, `refinement`, `counter`).
- `Evidence state` uses the stored value (`untested`, `supported`, `stressed`, `disputed`, or `—` if NULL).
- `Status` uses the stored value.
- For each metric column: use `value` (not `value_numeric`). Enums and short phrases display as-is. If `value_numeric` exists AND the metric is a scored criterion, do NOT display the number — display the ordinal label the user defined (e.g. write `high` / `mid` / `low` based on quartiles within the cohort). Raw scores do not belong in user-facing output.

**Step 5 — Write per-idea paragraphs.** Below the table, list each idea with:
- `## Idea #NN — <title>`
- The full `description` (immutable field, coffee-talk prose).
- Any `brilliance.tier='brilliant'` → include the pitch sentence.
- Any `web_stress_verdict` → include the strongest-surviving-objection rationale.
- Any `shortlist_reason` → include the rationale.
- Any `taste='picked'` → one line noting the user picked this idea in taste check.

**Step 6 — Write the report file** to `./.logbooks/ideation/$SLUG/reports/$RUN_ID-compare.md`. Create the directory if needed.

## Output discipline

- Follow `references/output-rules.md`. No raw scores, no composite numbers, no methodology names in the report text.
- The table is dense — each cell 1-3 words. The paragraphs below are where prose lives.
- File is idempotent per `$RUN_ID` — if the file exists, overwrite; the orchestrator owns uniqueness via `run_id`.
- Do NOT paste the table into the outcome summary; the summary points to the file path.

## Commands

```bash
# Read context
python scripts/ideation_db.py idea $SLUG $IDEA_ID
python scripts/ideation_db.py latest-assessment $SLUG --idea-id $IDEA_ID --metric feasibility

# Ensure reports dir
mkdir -p "./.logbooks/ideation/$SLUG/reports"

# Write the markdown report (pseudo — the operator generates content and writes to this path)
# Path: ./.logbooks/ideation/$SLUG/reports/$RUN_ID-compare.md
```

Example report skeleton the operator produces:

```markdown
# Comparison — run $RUN_ID

Cohort: 5 shortlisted ideas.

| # | Title | Kind | Evidence | Status | feasibility | novelty | web_stress | brilliance | taste |
|---|---|---|---|---|---|---|---|---|---|
| 12 | Triaged-touch model | hybrid | supported | shortlisted | high | high | survives_scrutiny | brilliant | picked |
| 34 | Pre-loaded workspace | variant | stressed | shortlisted | high | mid | weakened | — | — |
| ...

## Idea #12 — Triaged-touch model

<full description>

Brilliant pitch: <pitch sentence>.
Strongest surviving objection: <one sentence>.
Shortlist reason: <one sentence>.
User picked this in the taste check.
```

## Return

A 1-3 sentence outcome summary: how many ideas were compared, which metrics became columns, and the absolute path of the report file written.
