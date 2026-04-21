# Playbook: stress_test_shortlist

Take an existing shortlist (or near-shortlist) and subject it to web-sourced adversarial evidence. Updates evidence_state on the ideas and produces a comparison that highlights which ideas survive scrutiny.

## When to pick

- User says "stress-test the bold ones", "validate idea 17", "can these survive reality", "prove the top 3".
- Matches intent-shape: "stress/validate/prove <cohort>".
- The topic has scored ideas (evaluate.score has run at least once) OR the user explicitly names the cohort.

## When NOT to pick

- No ideas exist yet — run `deep_explore` or `quick_seed` first.
- No criteria have been defined and user wants scoring too — run `converge_existing` instead (it includes criteria + scoring before stress).

## Steps

1. decide.shortlist cohort=<cohort-from-intent-or-top-by-composite(5)>
2. CHECKPOINT: before_validation
3. validate.web_stress cohort=<same-as-step-1>
4. evaluate.score cohort=<same-as-step-1>   # rescore with new evidence
5. evaluate.brilliance cohort=<same-as-step-1>
6. decide.compare cohort=<same-as-step-1>

## Expected output

- Each cohort idea has a fresh `web_stress_verdict` assessment and a patched `evidence_state` (`supported` / `stressed` / `disputed`).
- New `facts` rows — both supports and adversarials — linked to the ideas via `evidence_fact_ids` on the assessments.
- Updated `score_summary` reflecting how the evidence shifted the composite.
- A comparison report surfacing the evidence shift (which ideas got stronger, which got weaker).

## Cohort resolution

If the user names a cohort ("the bold ones", "17 and 24"), the planner resolves it. If the intent is vague ("the top ones"), the planner defaults to `top-by-composite(5)` — which requires a prior `evaluate.score` run.

## Notes

- `evaluate.score` re-runs after web_stress because assessments for the criteria may weight evidence differently than the first scoring pass (e.g., a "feasibility" metric that took a hit from adversarial facts).
- `evaluate.brilliance` is included because stress-testing often reveals whether an idea has the "brilliant core" that survives negative evidence, or whether the idea's appeal was in the novelty alone.
- No new ideas are generated — this playbook is purely evaluative. Ideas that get disputed are NOT automatically rejected; the user decides what to do with them in a later `decide.converge`.
