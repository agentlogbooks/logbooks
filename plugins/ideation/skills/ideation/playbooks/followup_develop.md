# Playbook: followup_develop

Develop one or more specific existing ideas further by running multiple transforms, narrowing with a taste check, and comparing the resulting children.

## When to pick

- User says "develop idea 17", "deepen 42 and 58", "expand the strong ones".
- Matches intent-shape: "develop/deepen/expand/build-on <ID(s)>".
- The topic already has ideas — this is a follow-up session, not a fresh one.

## When NOT to pick

- The user wants two specific ideas combined (use `hybridize_pair`).
- The user wants validation of existing ideas (use `stress_test_shortlist`).

## Steps

1. transform.scamper(op=all) cohort=<cohort-from-intent>
2. transform.cross_domain cohort=<cohort-from-intent>
3. transform.invert cohort=<cohort-from-intent>
4. CHECKPOINT: taste
5. evaluate.taste_check cohort=children_of(<cohort-from-intent>)
6. decide.compare cohort=children_of(<cohort-from-intent>)

## Expected output

- 3–6 new children per parent idea (one or two per transform operator).
- Lineage edges from each child to its parent (the transforms set this automatically).
- A comparison report highlighting which children amplify vs. weaken the parent's core mechanism.

## Cohort resolution

The planner injects the parent ID(s) from the user's intent into every step. The `children_of` cohort keyword is resolved by the orchestrator at step time (so step 5's cohort is whatever the three transforms just produced).

## Notes

- The three transforms run sequentially (not parallel) so each can build on the intuitions surfaced by the previous one. If you need pure parallel fan-out, invoke a custom plan.
- No scoring or validation — follow-up development is exploratory. Score/validate the winning children in a separate invocation if they're worth pushing further.
- The taste-check is first-class: the user sees every child and picks favorites before any comparison report is written.
