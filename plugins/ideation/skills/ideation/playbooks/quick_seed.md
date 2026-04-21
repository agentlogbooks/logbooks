# Playbook: quick_seed

Intermediate ideation — `starter`'s flow plus web grounding, criteria derivation, and scoring. About twice as long as `starter`, less than a third of `deep_explore`. ~10 minutes of wall-clock time.

## When to pick

- The user explicitly asks for scoring, ranking, or prioritization ("rank these", "score them", "prioritize ideas for X").
- The topic is narrow enough that two personas cover the space but worth a scoring pass.
- You want `starter`'s shape but with a ranked compare report instead of a flat one.

## When NOT to pick

- The user gave no scoring/ranking signal — use `starter` (lighter, faster).
- The user wants comprehensive exploration — use `deep_explore`.
- The topic already has ideas and you're building on them — use a follow-up playbook.

## Steps

1. frame.context_scout
2. frame.discover
3. CHECKPOINT: framing
4. PARALLEL:
   - generate.seed(persona=innovator, count=12)
   - generate.seed(persona=wild_card, count=12)
5. evaluate.criteria
6. CHECKPOINT: criteria_lock
7. evaluate.score cohort=all_active
8. decide.compare cohort=top-by-composite(5)

## Expected output

- ~20–30 seed ideas in the logbook.
- One comparison report under `./.ideation/<slug>/reports/<run_id>-compare.md` ranking the top 5.
- No Johns, no ratchet, no web-stress, no brilliance — the cost of a quick pass is the absence of those signals.

## Notes

- Users who run `quick_seed` and then want more depth can re-invoke `ideation <slug>: continue exploring` — the planner will notice existing seeds and propose a natural extension (usually a John pass + score).
- No `decide.converge` here — quick_seed does not force a decision; `decide.compare` lets the user sit with the top 5 and pick their own direction.
