# Playbook: hybridize_pair

Combine two or more specific existing ideas into hybrid children, refine the hybrids, score them, and stress-test the winners.

## When to pick

- User says "combine 17 and 24", "hybridize the bold ones with the ICE cluster", "what if we merged these".
- Matches intent-shape: "combine/hybridize/merge <ID> and <ID>".

## When NOT to pick

- The user wants to develop one idea at a time (use `followup_develop`).
- The user wants to validate existing ideas without producing new ones (use `stress_test_shortlist`).

## Steps

1. transform.hybridize cohort=<cohort-from-intent>
2. transform.scamper(op=all) cohort=children_of(step 1)
3. evaluate.criteria
4. CHECKPOINT: criteria_lock
5. evaluate.score cohort=children_of(step 1)
6. CHECKPOINT: before_validation
7. validate.web_stress cohort=top-by-composite(3)
8. decide.compare cohort=children_of(step 1)

## Expected output

- 1–3 hybrid children (depending on how many parents in the cohort and how cleanly they combine).
- ~6–12 scampered variants on each hybrid (for a total of ~10–20 new ideas).
- Scored, stress-tested, and compared — the playbook exits with a ranked view of what the combination unlocked.

## Cohort resolution

- Step 1 cohort: the IDs from the user's intent, verbatim.
- Step 2 and later cohorts: `children_of(step 1)` or derived queries. The orchestrator resolves these by reading lineage rows emitted by step 1.

## Notes

- If the cohort in step 1 is 3+ ideas, `transform.hybridize` may produce a single "three-parent" child rather than a pair. That's fine — the lineage graph handles any number of parents.
- The scamper pass on the hybrids stress-tests whether the combination is robust to small variations. A hybrid that survives scampering is a stronger signal than one that wins the initial combine.
- `evaluate.criteria` is rerun in this playbook (not inherited from a prior session) because hybrid children often open new dimensions of evaluation. Users who want to reuse existing criteria can drop this step via `--edit-plan`.
