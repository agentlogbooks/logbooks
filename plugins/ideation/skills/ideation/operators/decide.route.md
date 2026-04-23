---
name: decide.route
stage: decide
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - pool has a mix of idea states and next moves are not obvious
  - mid-flow decision on what to do with each of a batch of ideas
avoid_when:
  - pool is too small to warrant routing (fewer than 5 ideas)
  - intent is a single-shape bulk operation (use the direct playbook instead)
produces:
  ideas: false
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups: []
---

# Operator: decide.route

Read a cohort of active ideas plus the operator catalog, decide per-idea (or per-pair) which operator to run, and emit a plan fragment the orchestrator will expand inline.

## Inputs

- `cohort_ids`: 1+ ideas — typically the output of `all_active_capped(50)`.
- `params`:
  - `cheap` (bool, default `false`) — when true, avoid operators with `cost.web: true`.

## Reads

- **Operator catalog** — provided inline in the subagent prompt by the orchestrator (from `list-operators --format yaml`). Do not shell out for it.
- **Active frame** via `ideation_db.py active-frame $SLUG`.
- **Each idea** via `ideation_db.py idea $SLUG $IDEA_ID` — returns the idea row plus `latest_assessments_by_metric` in one call.
- **Lineage history per idea** via `ideation_db.py lineage-ops $SLUG $IDEA_ID --limit 5` — used to enforce cooldowns.

## Semantics of `produces`

The catalog's `produces` flags name each operator's **primary** artifact — the thing the router should expect to appear after the operator runs. A few operators optionally write secondary artifacts (e.g., `evaluate.tension` and `evaluate.hats` can occasionally emit bridge variant ideas; `transform.ratchet` can write a `tension.ratchet_status` assessment). Do not plan against secondary artifacts. If the router needs a new idea, pick a `transform.*`; if it needs an assessment, pick an `evaluate.*`; if it needs facts, pick a `validate.*`.

## Decision procedure

For each idea in `cohort_ids`:

1. Read the idea and its lineage-ops history.
2. Compute the set of **candidate operators** from the catalog that pass the hard gates:
   - The idea's `kind` is in the operator's `applies_to.kinds` (unless `applies_to.kinds` is empty — those are pool-scope and not assignable per-idea anyway; skip them for per-idea decisions).
   - If `params.cheap` is set, drop operators with `cost.web: true`. If this eliminates every remaining candidate for an idea (no non-web operators pass the other gates), park that idea with reason "no non-web operators available".
   - The operator's `repeat_guard.same_lineage_cooldown` is not violated — an operator is on cooldown for this idea if it appears in the `same_lineage_cooldown` most-recent entries returned by `lineage-ops`. If `same_lineage_cooldown` is 0, the operator is never on cooldown. Note: `lineage-ops` is queried with `--limit 5`, so cooldowns above 5 are effectively capped at 5 — currently no operator has a cooldown above 2, but revisit this limit if one is added.
3. Among the candidates, use `use_when` / `avoid_when` as soft judgment cues. Pick the single best operator, or one of:
   - **Pair this idea with another** — if two ideas in the cohort have complementary mechanisms or sit in tension, recommend `transform.hybridize cohort=[i,j]` (scope=group, min_cohort=2). Emit this as a single fragment line covering both ideas, not two separate recommendations. Before emitting a hybridize line, verify that `transform.hybridize` clears the cooldown gate on **both** ideas' lineage histories — if it's on cooldown for either one, skip the pair.
   - **Park** — with a one-line reason, for ideas that are too vague, already exhausted, or left with no viable operator. Parking is a *lifecycle* decision, not just a per-run label: for every parked idea, patch its status to `parked` by calling `ideation_db.py patch-idea $SLUG <idea_id> status parked` before writing the report. This removes the idea from `all_active_capped(50)` on future `--loop` iterations so the router does not re-decide the same pool every pass. Users reactivate a parked idea by hand with `ideation_db.py patch-idea $SLUG <idea_id> status active`.

## Output — run-scoped report file

Write `./.ideation/$SLUG/reports/$RUN_ID-route.md` with exactly two sections:

```markdown
## Routing (batch of N ideas)

| IDs | Operator | Reason |
|---|---|---|
| 8 | transform.invert | promising but brittle; no recent invert on this lineage |
| 14, 19 | transform.hybridize | complementary mechanisms, both BOLD |
| 20, 22, 25 | — park | assumptions too vague to mutate productively |

## Plan fragment

PARALLEL:
- transform.invert cohort=[8]
- transform.hybridize cohort=[14, 19]
```

The `## Plan fragment` section uses the exact grammar below. The orchestrator parses it.

### Plan fragment grammar

```
PARALLEL:
- <operator.name> [key=value ...] cohort=[id, id, ...]
- <operator.name> [key=value ...] cohort=[id, id, ...]
```

Rules:
- Exactly one `PARALLEL:` header.
- Each subsequent non-blank line is a `- operator.name ...` bullet.
- `cohort=[...]` is mandatory, literal integer IDs only.
- Params are space-separated `key=value`; no quotes, no spaces in values.
- The orchestrator coerces each value: `^-?\d+$` → integer, `true`/`false` → boolean, otherwise string. Keep integer and boolean params unquoted; otherwise downstream operators receive a string.
- Parked ideas are listed in the `## Routing` table only, never in the plan fragment.

## Edge cases

- **Empty cohort** → write an empty `## Plan fragment` section (header with no bullets). Outcome summary: "nothing to route."
- **No active frame** → fail fast; this should have been caught by the `route` playbook's preconditions.
- **All ideas parked** → empty plan fragment. All cohort ideas also get their status patched to `parked` per the Decision procedure, so the next iteration's `all_active_capped(50)` will return an empty cohort — in `--loop` mode, that terminates the loop via the empty-fragment exit.

## Commands

```bash
# Read frame
python scripts/ideation_db.py active-frame $SLUG

# For each idea:
python scripts/ideation_db.py idea $SLUG $IDEA_ID
python scripts/ideation_db.py lineage-ops $SLUG $IDEA_ID --limit 5

# Park an idea (lifecycle transition — apply to every idea listed with "park" in the routing table):
python scripts/ideation_db.py patch-idea $SLUG $IDEA_ID status parked
```

## Return

1–3 sentence outcome summary: how many ideas routed, how many parked, headline decisions ("Routed 14 ideas across 4 operator assignments; parked 4; strongest call was pairing ideas 14 and 19 for hybridize").
