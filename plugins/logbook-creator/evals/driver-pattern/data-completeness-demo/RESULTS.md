# Data-completeness test — results

A multi-phase, data-accumulating workflow logbook (`firmographics → techstack → contacts → score`)
built by following `logbook-creator` (driver variant, Step 2.5), then tested for data completeness.
Reproduce: `python3 harness.py && python3 audit.py` (exit 0 = pass).

## Local test (`audit.py`)

Driver logbook, 12 rows → partition **9 complete + 1 in-flight + 2 parked = 12**. All nine invariants PASS:
partition-total, DAG-monotonic, sentinel-integrity, field-fill (×4), poison-cap, no-leaked-claim.

Naive contrast schema (no sentinels/attempts): can only see **8 "complete" / 4 "pending"** — misclassifies
the two legit-empty rows as pending and the two poison rows as in-progress. Completeness **unprovable**.

## Independent verification (9-agent workflow, run `wf_5fd4dfcc-4c5`)

**Six independent auditors**, each writing its *own* SQL against the real DB (not trusting `audit.py`):
all six **confirmed, zero violations, zero counterexamples** — partition (incl. pairwise mutual-exclusivity
of the hard buckets), DAG monotonicity across all three edges, sentinel integrity (`quote()` over distinct
values shows only proper literals, no `''`), field-vs-status, poison/dead-letter ({wonka, cyberdyne}),
claim/lease integrity.

**Naive contrast (independent):** `provable = false`. Two structural collisions make it unfixable by *any*
content-only query: `umbrella`(COMPLETE, none-detected) ≡ `cyberdyne`(PARKED, poison) share a byte-identical
NULL signature; `wayne`(IN-FLIGHT) ≡ the finished rows. Best content-only predicate scores **7/12**. This is
the proof of *why* the status sentinel + lease are load-bearing for completeness.

**Completeness critic — one real finding (latent liveness gap, not a violation in the current data):**
`<stage>_attempts` is incremented at *error/release*, not at *claim*. A worker can claim a row, crash before
doing any work, let the lease expire, and the row is silently reclaimed with `attempts` unchanged — an
unbounded claim→crash→reclaim loop that the attempts cap never trips and that no *snapshot* invariant can
detect. The current data is still provably complete (no crash is modeled), but the **schema cannot detect a
hypothetical crash-loop**.

### Generic refinement this implies (candidate for the skill — not yet validated by the eval loop)

Driver Decision 2/4: **count attempts at *claim* time, or add a dedicated `claim_count`/`lease_epochs`
column**, and have the **reclaim path itself park** a row whose claim-count ≥ N (a reaper), rather than
relying on a worker reaching the error branch. Otherwise a crashed-mid-lease row is the one liveness hole a
point-in-time completeness audit cannot see. Worth folding into `references/work-queue.md` and re-validating
through the driver persona eval loop before shipping.

## Deterministic visualization (render projection)

`render.py` is an **export-only projection**: `view = render(driver.db)`, a pure read-only function of
the store. `step_trace.py` writes an append-only **run-trace** (`driver.history.jsonl`) so the view can
also show the burndown. Reproduce: `python3 harness.py && python3 step_trace.py && python3 render.py`.

Proven (`render.py` over the live `driver.db`):

- **Deterministic** — render twice, the full-file sha256 is identical (`c946ea369442bf02`). No clock, no
  randomness, no network, no hand-typed numbers. `now` is a *query parameter* (default `2026-06-11T12:00:00Z`,
  same as `audit.py`), not the wall clock — that is what keeps it reproducible.
- **Faithful** — the view's partition (`9 complete / 1 in-flight / 2 parked = 12`) is the *same* partition
  `audit.py` verifies. The picture cannot drift from the audit because it is the audit's data, rendered.
- **Progressive at every fill level** — all 44 run-trace frames (empty → fixpoint) sum to 12; the burndown
  shows pending 11→0, complete 0→9, parked 0→2, in-flight steady at 1. "Progressive" = correct at *every*
  fill level, not just when full.
- **Follows the store** — mutate the store (expire `wayne`'s lease: in-flight → pending) and re-render; the
  view follows deterministically to `9 complete / 2 parked / 1 pending = 12`. Deterministic in state,
  progressive in time.
- **Read-only** — `driver.db`'s sha256 is unchanged after rendering. A render that wrote to the store would
  be a *mirror*, not a projection.
- **Temporal capability is upstream** — the burndown exists *only* because the append-only run-trace retained
  history. A patch-in-place ledger could render the current snapshot only; a single snapshot has no
  trajectory. (Decided back at state-architecture / projections, not in the renderer.)

This is the RED→GREEN for visualization: the hand-authored `data-completeness-explained.html` (numbers typed
by hand) is the RED — a second source of truth that drifts the instant `harness.py` changes a number;
`render.py` is the GREEN — a projection that *cannot* drift. The committed `driver.view.html` is the exported
snapshot a human opens; the `.db` and `.jsonl` are gitignored (rebuildable).

## Verdict

The driver logbook is **provably data-complete at any snapshot** (every row accounted for; every `done` cell
provably populated; legit-empty distinguished from pending; poison parked and surfaced). The one gap is
*liveness over time* (crash-reclaim loop), addressable with claim-time counting + a reaper. The naive schema
cannot prove completeness at all — establishing that the driver pattern's sentinels are what make
data-completeness a query rather than a guess.
