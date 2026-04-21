# Playbook: starter

Lightweight default. Frame the problem in one step, generate ~20 ideas in parallel from two personas, present them side-by-side. One checkpoint (framing), no scoring, no web stress. A good starting point for almost any brainstorm — follow up with heavier playbooks only if the output warrants it.

## When to pick

- **Default for fresh topics.** If the user says "brainstorm", "ideate", "give me ideas for X", or the intent has no signal either way, pick this.
- The topic is fresh or very early — no prior ideas in the logbook yet.
- The user wants to see output quickly (under ~5 minutes of wall clock time).

## When NOT to pick

- User explicitly asks for "deep" / "thorough" / "full treatment" / "explore every angle" — use `deep_explore`.
- User asks for scoring or ranking — use `quick_seed`.
- Topic already has ideas — use a follow-up playbook.

## Steps

1. Identify root causes and framing questions (frame.discover)
2. ⏸ Checkpoint — confirm the framing before generating ideas
3. Generate ~20 diverse ideas in parallel:
   - Practical, contradiction-driven ideas — 10 (generate.seed persona=innovator count=10)
   - Wild, random-stimulus ideas — 10 (generate.seed persona=wild_card count=10)
4. Present them side-by-side in a short report (decide.compare cohort=all_active)

## Expected output

- One frame row capturing root causes + HMW.
- ~20 seed ideas in the logbook.
- One markdown report under `./.ideation/<slug>/reports/<run_id>-compare.md` rendering all ideas with their tags and one-line descriptions.

## Notes

- No `frame.context_scout` — the web-search pass is valuable but adds minutes of wall-clock time. Starter skips it; if the user wants grounding, they can re-invoke `ideation <slug>: dig deeper with web research` and the planner will add it.
- No `evaluate.criteria` / `evaluate.score` — starter is about generating and seeing, not ranking. The user can follow up with `converge_existing` or `stress_test_shortlist` on ideas that interest them.
- Two personas covers most of the idea space for a first pass. Follow-up invocations add more personas / transforms as needed.
- The framing checkpoint is the only user interruption. If the user passed `--no-checkpoints`, even that is skipped and the session runs fully autonomous.
