# Playbook: reframe_and_regenerate

User changed their mind about the problem. Record a new frame (preserving the old), then regenerate seeds under the new framing and optionally transform.

## When to pick

- User says "actually, the real problem is X", "let me restate this", "I want to reframe", "the problem isn't X it's Y".
- Matches intent-shape: "reframe / rethink / the problem is actually <new statement>".
- Prior ideas under the old frame should stay queryable (they carry `frame_id_at_birth` from the old frame).

## When NOT to pick

- The framing stayed the same but the user wants different ideas (use `followup_develop` or `deep_explore` re-run).
- The user is only editing one HMW question or root cause — pass that as a note during the `frame.discover` checkpoint instead.

## Steps

1. frame.reframe
2. CHECKPOINT: framing
3. PARALLEL:
   - generate.seed(persona=innovator, count=12)
   - generate.seed(persona=wild_card, count=12)
4. transform.john(zone=FIRE, stance=dreamer_start) cohort=all_seeds
5. evaluate.criteria
6. CHECKPOINT: criteria_lock
7. evaluate.score cohort=all_active
8. decide.compare cohort=top-by-composite(5)

## Expected output

- One new `frames` row (version N+1, active=1, supersedes the old).
- Old frame's `active=0`, but still readable — old ideas retain `frame_id_at_birth` pointing at it.
- 20–30 new seeds + a John pass, scored and compared under the new framing.

## Notes

- Ideas generated before the reframe are NOT invalidated or deleted. They remain queryable and can be hybridized with new ideas later (`hybridize_pair` across frames is perfectly valid — it often surfaces that the old frame captured something the new one missed).
- Only two personas here (vs. four in `deep_explore`) because a reframe session is usually shorter — the user wants to see quickly what the new framing unlocks before committing to a full treatment. Users who want four personas under the new frame can run `deep_explore` as a follow-up.
- `frame.reframe` automatically flips the old frame's `active` flag — you never manually manage it.
