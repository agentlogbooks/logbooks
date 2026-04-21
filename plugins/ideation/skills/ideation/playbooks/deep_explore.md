# Playbook: deep_explore

Full-treatment ideation for a fresh problem. Scout the problem space, generate from four specialist personas, transform across temperature zones, evaluate, validate, and converge on a small number of selected ideas. Port of the v9 STANDARD/DEEP flow into the first-class-idea architecture.

## When to pick

- **Explicit opt-in only.** The user said "thorough" / "deep" / "full treatment" / "explore every angle" / "dig in" / "comprehensive" or the user explicitly passed `--playbook deep_explore`.
- The problem is strategic enough to justify ~15 subagent spawns and 15–30 minutes of wall-clock time.

## When NOT to pick

- **Default case — user said "brainstorm" / "ideate" / "ideas for X" with no modifier.** Use `starter`.
- The user asked only for scoring/ranking — use `quick_seed`.
- The user already has a shortlist and wants validation — use `stress_test_shortlist`.
- The user wants to build on specific existing ideas — use `followup_develop`.

## Steps

1. frame.context_scout
2. frame.discover
3. CHECKPOINT: framing
4. PARALLEL:
   - generate.seed(persona=innovator, count=15)
   - generate.seed(persona=provocateur, count=12)
   - generate.seed(persona=wild_card, count=15)
   - generate.seed(persona=connector, count=12)
5. PARALLEL:
   - transform.john(zone=FIRE, stance=dreamer_start) cohort=all_seeds
   - transform.john(zone=PLASMA, stance=realist_start) cohort=all_seeds
   - transform.john(zone=ICE, stance=critic_start) cohort=all_seeds
6. evaluate.tension cohort=all_active
7. transform.ratchet(zone=FIRE, cycles=2) cohort=tension_cluster
8. CHECKPOINT: taste
9. transform.hybridize cohort=diversity-top(5)
10. evaluate.criteria
11. CHECKPOINT: criteria_lock
12. evaluate.score cohort=all_active
13. CHECKPOINT: before_validation
14. validate.web_stress cohort=top-by-composite(8)
15. evaluate.brilliance cohort=top-by-composite(5)
16. CHECKPOINT: before_decide
17. decide.converge cohort=top-by-composite(3)
18. decide.export(format=menu)

## Expected output

- ~50–80 active ideas in the logbook at peak (before shortlist).
- 3–5 selected ideas after `decide.converge`.
- Four report artifacts under `./.ideation/<slug>/reports/<run_id>-*.md`.

## Notes

- The checkpoint rhythm is built in; running with `--no-checkpoints` strips them for fully autonomous runs (log the intent in the user's prompt).
- `diversity-top(5)` before hybridize ensures the hybridization pairs span zones and tags, not just the highest-scoring cluster.
- Brilliance runs only on the top 5 by composite score — it is not a universal pass.
