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

## Verdict

The driver logbook is **provably data-complete at any snapshot** (every row accounted for; every `done` cell
provably populated; legit-empty distinguished from pending; poison parked and surfaced). The one gap is
*liveness over time* (crash-reclaim loop), addressable with claim-time counting + a reaper. The naive schema
cannot prove completeness at all — establishing that the driver pattern's sentinels are what make
data-completeness a query rather than a guess.
