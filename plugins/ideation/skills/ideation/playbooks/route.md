# Playbook: route

Decide what to do next with the active pool, idea-by-idea. The router (a `decide.route` subagent) reads the operator catalog plus each idea's state, then emits a plan fragment — per-idea operator assignments plus pair groupings — which the orchestrator expands inline and executes.

## When to pick

- User says "route", "iterate", "keep going", "what should I try next", "plan next moves on the current pool".
- Topic already has at least 3 active ideas in a mixed state (no single-shape follow-up would cover the batch usefully).
- You've done a first-pass generate + transform burst and want a state-driven next step rather than another blanket operator.

## When NOT to pick

- User names specific idea IDs — use `followup_develop`, `hybridize_pair`, or `stress_test_shortlist` instead.
- Fewer than 3 active ideas — generate or seed more first.
- No active frame — run `starter` or `frame.discover` first.
- Bulk single-shape operation is what the user wants ("hybridize everything", "score everything") — use the direct playbook.

## Params

- `--loop` — iterative mode; after each fragment executes, the router re-runs against the updated pool, up to `--iterations`.
- `--cheap` — passes `params.cheap=true` to `decide.route`; router avoids operators with `cost.web: true`.
- `--with-criteria` — inserts `evaluate.criteria` + `evaluate.score cohort=all_active` (with `CHECKPOINT: criteria_lock` between them) before routing.
- `--iterations N` (default `3`, max `3`) — caps loop iterations when `--loop` is set. Ignored otherwise.

## Steps (default, single-pass)

1. Route the active pool, capped at 50 (decide.route cohort=all_active_capped(50))

The orchestrator expands the plan fragment emitted by step 1 inline — no separate step required here.

## Steps (--with-criteria)

1. Derive evaluation criteria (evaluate.criteria)
2. ⏸ Checkpoint — lock the criteria
3. Score every active idea against the criteria (evaluate.score cohort=all_active)
4. Route the active pool, capped at 50 (decide.route cohort=all_active_capped(50))

## Loop behavior (--loop)

When `--loop` is set, the orchestrator re-enters the playbook body after the fragment finishes executing. Termination conditions (any one terminates the loop):

- The latest `decide.route` produced an empty plan fragment (no operator calls emitted) — nothing more to route.
- Iteration count reaches `--iterations N` (default 3).
- User declines at the iteration checkpoint (unless `--no-checkpoints` was passed).

The `run_id` stays the same across all iterations. Every operator run inside the loop shares that `run_id`, so post-run aggregation sees the whole session.

## Preconditions

Checked by the playbook before invoking the planner. Pre-flight, not an operator step:

1. Active frame exists — else error: "No active frame. Run `ideation <slug>: <intent>` with the `starter` playbook or `frame.discover` first."
2. At least 3 active ideas — else error: "Pool has fewer than 3 active ideas. Run `generate.seed` or the `starter` playbook first."

## Expected output

- Zero or one `## Routing` report at `./.ideation/<slug>/reports/<run_id>-route.md`.
- Zero or more operator runs from the expanded fragment (each a normal `operator_runs` row under the same `run_id`).
- In `--loop` mode, multiple `decide.route` runs (one per iteration) plus their expansions.

## Notes

- `route` does not replace `followup_develop`, `hybridize_pair`, or `stress_test_shortlist`. Those remain for cases where the user names specific ideas.
- `deep_explore` does not call `route` internally in v1.
- The router never emits pool-scope operators (`evaluate.tension`, `decide.compare`, etc.) — those are playbook-shape concerns. Use the direct playbook if the pool as a whole needs that kind of move.
