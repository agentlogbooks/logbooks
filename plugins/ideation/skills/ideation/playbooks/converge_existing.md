# Playbook: converge_existing

No new ideas — the topic already has a healthy candidate pool and the user wants to decide. Derive criteria, score, stress, and converge.

## When to pick

- User says "decide on what we have", "pick the best of these", "let's converge", "final call on the current batch".
- Matches intent-shape: "decide / pick / final / converge / choose".
- The topic has at least a dozen active ideas already.

## When NOT to pick

- The topic is fresh — run `deep_explore` instead.
- The user wants more ideas before deciding — run `followup_develop` or another generation playbook first.

## Steps

1. evaluate.criteria
2. CHECKPOINT: criteria_lock
3. evaluate.score cohort=all_active
4. CHECKPOINT: before_validation
5. validate.web_stress cohort=top-by-composite(8)
6. evaluate.brilliance cohort=top-by-composite(5)
7. CHECKPOINT: before_decide
8. decide.converge cohort=top-by-composite(3)
9. decide.export(format=menu)

## Expected output

- Every active idea has at least one scoring pass against the derived criteria.
- Top 8 have fresh web-stress assessments.
- Top 5 have brilliance assessments.
- 1–3 ideas with `status='selected'`, others with `status='rejected'` or unchanged if the user deferred.
- A converge report capturing the rationale + a menu export rendering Quick Wins / Core Bets / Moonshots.

## Notes

- No generation or transformation happens in this playbook — it is pure evaluation + decision. This is why the cohort counts are tight (the pool is whatever was already in the logbook).
- If there are no active ideas, the orchestrator fails at step 3 rather than silently producing an empty report.
- Users running this mid-session who find the criteria don't fit can use the `criteria_lock` checkpoint to edit them; the edits feed back through `evaluate.score` transparently.
- Reusing prior criteria from an earlier run: edit the plan at the approval step to remove `evaluate.criteria` and pass `criteria_path` explicitly to `evaluate.score`. The planner does not do this automatically — by default, each converge session derives its own criteria so it can respond to any new ideas added since the last run.
