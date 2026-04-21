# Operator: evaluate.taste_check

Ask the user to pick their favorite ideas from a diverse slate, then record a binary `taste` assessment per presented idea. This is the single operator permitted to spawn `AskUserQuestion` during evaluation — its whole purpose is a lightweight human gate.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to present to the user. Typically 10 — assembled by the orchestrator to span multiple tags / zones / kinds.
- `params`:
  - `question_label` (string, default `"Which of these resonate with you?"`) — the prompt text shown to the user.
  - `batch_size` (int, default 4) — options per `AskUserQuestion` call; `AskUserQuestion` caps at 4 discrete options plus auto "Other". If the cohort exceeds `batch_size`, issue multiple rounds.

## Outputs

- `assessments` rows: one `metric=taste` row per presented idea. `value` is `picked` or `not_picked`; `value_numeric` is `1` or `0`; `rationale` is empty or a short note ("user picked in round 2 of 3").
- No external files. No ideas are mutated. No facts written.

## Reads

- Each cohort idea row via `ideation_db.py idea $SLUG $IDEA_ID` (title + description for display).

## Prompt body

Spawn `AskUserQuestion` with up to `batch_size` options per call. Each option shows the idea ID and title so the user can identify it later. Split the cohort into rounds if needed:

- Round 1: ideas 1-4 of the cohort
- Round 2: ideas 5-8 of the cohort
- Round 3: ideas 9-10 of the cohort (plus two "see previous rounds" or "done" options if useful)

Allow the user to pick as many as they like — `AskUserQuestion` is single-select per call, so phrase the option text as one idea each and collect selections across rounds. Record each option selected as `taste=picked` (value_numeric=1) and each option NOT selected as `taste=not_picked` (value_numeric=0).

If the user aborts mid-rounds (selects a meta-option like "none of these" or closes the flow), record `not_picked` for all remaining cohort ideas and return early.

This operator does NOT filter the cohort. Taste is one signal — later scoring or decide operators may weight it, but non-picked ideas stay in the pool.

## Output discipline

- Follow `references/output-rules.md`. Do not display scores, rankings, or methodology in the `AskUserQuestion` options. Each option is `"Idea #NN: <title>"` plus at most a one-sentence description.
- Never truncate an idea description into jargon. If it exceeds a reasonable option length, use the title + the first sentence of the description.
- Do not persist a "user favorites" boost multiplier in the logbook — the scoring operator reads `taste` assessments and decides weighting itself.

## Commands

**Batch every write.** For a cohort of N presented ideas, this operator should produce exactly 1 write subprocess call total (one `add-assessments-batch` with all N `taste` rows) after all `AskUserQuestion` rounds have completed — regardless of how many rounds or how many picks. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read cohort rows for display (per-row reads are fine)
python scripts/ideation_db.py idea $SLUG $IDEA_ID

# Use AskUserQuestion with up to batch_size options per call:
#
# AskUserQuestion:
#   question: "Which of these resonate with you? (round 1 of 3)"
#   header: "Taste Check"
#   options:
#     - "Idea #12: Triaged-touch model"
#     - "Idea #34: Pre-loaded workspace"
#     - "Idea #47: Anonymous posting"
#     - "Idea #58: Pay-per-outcome pricing"
#
# Collect user picks across ALL rounds first, then write every taste row in one batch:
cat > /tmp/taste-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "taste", "value": "picked", "value_numeric": 1,
   "rationale": "User picked in round 1 of 3"},
  {"idea_id": 34, "metric": "taste", "value": "not_picked", "value_numeric": 0},
  {"idea_id": 47, "metric": "taste", "value": "picked", "value_numeric": 1,
   "rationale": "User picked in round 2 of 3"},
  {"idea_id": 58, "metric": "taste", "value": "not_picked", "value_numeric": 0},
  {"idea_id": 71, "metric": "taste", "value": "not_picked", "value_numeric": 0,
   "rationale": "User aborted after round 2; auto-recorded as not_picked"}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/taste-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/taste-$OPERATOR_RUN_ID.json
```

**Do not** call `add-assessment` per idea. The batch form is strictly faster and preserves transactional atomicity.

## Return

A 1-3 sentence outcome summary: how many rounds were run, how many ideas the user picked vs. skipped, and any ideas recorded as `not_picked` due to early abort.
