# Driver (work-queue) logbooks

Internal documentation for the driver branch (SKILL.md Step 2.5). A **driver logbook** is one where
**the schema is a state machine and an empty stage cell is the trigger for an agent to do that stage.**
`WHERE <stage>_status IS NULL` *is* the work queue; `GROUP BY` over the stage statuses is a live
burndown. The durable store replaces the in-context todo list, so work is resumable after a crash,
parallelizable, and auditable.

This file is generic. The rules and templates use placeholders (`<stage>`, `<prior>`, `N`); a single
worked example at the end makes them concrete. Do not copy the worked example's stage names into a real
spec — derive the user's own.

## When it applies (and the guard that must not be skipped)

The driver gate fires when an empty cell signals pending work. It is a property *layered on* a logbook
that already qualifies — it is **not** a licence to skip the Step 1 "three of four" test. A driver
logbook is a **blackboard** (agents *pull* empty cells); it is not a tracker. The moment the need
includes per-person assignment, due dates, notifications, or staleness SLAs, it is work-management
(Jira/Linear), not a logbook. Keep that line bright (decision 5).

The driver dimension is **orthogonal** to single-table vs. multi-entity (Step 2.4): a flat queue and a
multi-entity pipeline can both be drivers.

## The five decisions (generic rules)

### 1. Sentinel — "empty" must mean exactly one thing

The failure: triggering on a **content** column's emptiness ("empty `result` ⇒ do the work"). It breaks
the instant a stage completes successfully but legitimately produces no content — that row stays empty
and is re-processed forever.

**Rule:** never trigger on a content column. Every stage gets a dedicated status column:

```
<stage>_status :  NULL = pending  |  'done'  |  '<terminal-skip>'  |  'failed' (parked)
```

`NULL` is reserved for *pending* exclusively — a status column never holds empty-string (a worker
writing `""` is indistinguishable from pending). Content columns the stage fills (`summary`, `score`,
`comment`) may be empty when `<stage>_status = 'done'`. The trigger and every ready-query read the
status column, never the content column.

### 2. Concurrency — claim a row before working it

The failure: N workers all run `WHERE <stage>_status IS NULL`, all grab the same top row, all do the
work. **Rule:** claim atomically, with an expiring lease so a crashed worker's row is reclaimable.

Generic columns (row-level lease — sufficient when a row is worked at one stage at a time):
`claimed_by TEXT`, `claimed_at TEXT`, `lease_until TEXT` (ISO-8601).

```sql
-- atomic claim of the next ready row for <stage> (SQLite: one statement = one transaction)
UPDATE <table>
   SET claimed_by = :worker, claimed_at = :now, lease_until = :now_plus_lease,
       <stage>_attempts = <stage>_attempts + 1          -- count at CLAIM time: crashes count (decision 4)
 WHERE id = (
   SELECT id FROM <table>
    WHERE <stage>_status IS NULL
      AND (lease_until IS NULL OR lease_until < :now)   -- unclaimed or lease expired
      AND <stage>_attempts < N                          -- not poisoned (decision 4)
      AND <prior>_status = 'done'                        -- prerequisite met (decision 3)
    ORDER BY added_at
    LIMIT 1)
RETURNING id, <content cols>;                            -- empty result ⇒ nothing ready
```

This is why **storage flips**: CSV cannot claim atomically, so a concurrently-claimed driver requires
SQLite (or an enforced single writer). Overrides the "deprioritize SQLite in a repo" default.

The lease makes a dead worker's row *reclaimable* — that is recovery, not accounting. Decision 4
makes the reclaim *bounded*: the claim itself increments the attempts counter, because a worker that
crashes never reports.

### 3. Dependencies — readiness includes the prerequisite

Stages usually form a small DAG. "Ready for `<stage>`" is **not** `<stage>_status IS NULL` alone — it is
`<stage>_status IS NULL AND <prior>_status = 'done'`. Elicit the ordering; emit one ready-query per
stage carrying its prerequisite. (For a parallel fan-in, the predicate ANDs several prior stages.)

### 4. Failure — count at claim, park on reclaim (attempts + reaper + dead-letter)

The obvious failure: a row that can never complete (dead link, corrupt input) is re-claimed forever
and starves everything behind it. The subtle one: a row that *kills* its worker (crash, OOM-kill,
spot preemption) never reaches the worker's error branch — an error-time counter (`on error:
attempts += 1`) stays at 0 while the lease silently expires, and the row loops claim → crash →
reclaim **forever**. No snapshot audit can see that loop: every point-in-time check looks healthy
(row pending or validly leased, counter under cap); only retained history shows the row never
finishes. It is a liveness hole, not a safety hole.

**Rule:** count attempts at **claim** time — the atomic claim increments the counter (decision 2's
template), so a vanished worker still counts — and the **reclaim path itself parks** exhausted rows
(a reaper), so parking never depends on a worker surviving to report.

```
on claim:     <stage>_attempts += 1   (inside the atomic claim UPDATE — counts claims, so crashes count)
on success:   <stage>_status = 'done'; write content; release lease
on reported error:
              terminal error (input can never succeed) → <stage>_status = 'failed'; release lease
                                                          (park immediately — do not retry N times)
              transient error → release lease (retry; the next claim re-increments)
              if <stage>_attempts >= N → <stage>_status = 'failed'   (budget exhausted on the final try)
reaper (on the reclaim path, or a sweep at the top of each poll pass):
              UPDATE <table>
                 SET <stage>_status='failed', claimed_by=NULL, claimed_at=NULL, lease_until=NULL
               WHERE <stage>_status IS NULL AND <stage>_attempts >= N
                 AND (lease_until IS NULL OR lease_until < :now)
```

Distinguish transient reported failure (release, retry) from terminal (park) — silent crashes are
bounded by the same claim counter. Every ready-query includes `<stage>_attempts < N`. Three
consequences to record:

- **Size `N` with headroom** — claims are what is counted, so benign interruptions also consume
  budget (genuine tries + expected crash burn), and give dead-letter triage a defined requeue
  (reset `<stage>_attempts`, clear the lease).
- **The exhaustion invariant is lease-aware** — attempts may legitimately equal `N` while the Nth
  claim is still in flight. The violation, and the reaper's job, is an exhausted row *at rest*:
  pending, past the cap, lease expired or absent.
- **Liveness becomes checkable** — "every row eventually completes or parks" turns into the safety
  invariant *no pending row sits at rest with `attempts >= N`*; the full claim-bound (`no (row,
  stage) claimed more than N times`) is auditable only against retained history (a run-trace),
  never against a single snapshot.

### 5. Terminal outcomes — name what does not advance

Stage cells carry *outcomes*, not booleans. `'<terminal-skip>'` (e.g. `irrelevant`, `rejected`,
`duplicate`) and the final stage's verdict are **done-but-do-not-advance**. Because the next stage's
ready-query requires the prior status to be exactly `'done'`, a skipped/parked row never advances. Name
which status values advance and which absorb.

## Generic column kit

For each stage a driver logbook contributes:

| Column | Purpose |
|---|---|
| `<stage>_status` | `NULL`=pending trigger; `'done'`; terminal-skip value(s); `'failed'` |
| `<stage>` content col(s) | what the stage produces (may be empty when done) |
| `<stage>_attempts` | claim counter — incremented inside the atomic claim, so crashes count (decision 4); ready-query keeps `< N` |
| `claimed_by`, `claimed_at`, `lease_until` | shared row-level lease (decision 2; only if concurrent) |

Plus the usual logbook columns (`id`, an `added_at`/order key, and `author` when scope is shared).

## Generic query kit (for the spec's `## Queries`)

- **ready-query** (per stage): `… WHERE <stage>_status IS NULL AND <prior>_status='done' AND <stage>_attempts < N AND (lease_until IS NULL OR lease_until < :now)`
- **atomic claim**: the `UPDATE … WHERE id=(SELECT … LIMIT 1) RETURNING …` above — including the `<stage>_attempts + 1` increment (decision 4).
- **reaper** (decision 4 — run on the reclaim path or at the top of each poll pass): parks exhausted rows at rest: `UPDATE … SET <stage>_status='failed', claimed_by=NULL, claimed_at=NULL, lease_until=NULL WHERE <stage>_status IS NULL AND <stage>_attempts >= N AND (lease_until IS NULL OR lease_until < :now)`.
- **funnel** (live burndown — the payoff): one `count(*)` per stage `UNION ALL`'d, plus `parked` and `done`.
- **parked rows for a human**: `… WHERE <stage>_status='failed' OR <final>='<human-escape value>'`.

**SQLite NULL caveat:** `NULL != value` evaluates to `NULL` (not true), so `WHERE <stage>_status != 'failed'` silently drops pending (`NULL`) rows — the opposite of what a "still-active" query wants. Write `WHERE <stage>_status IS NULL OR <stage>_status != 'failed'` (or `IS NOT 'failed'` on SQLite 3.x) whenever a status filter must keep the pending rows.

## Spec sections (driver variant)

Extend the standard spec template with:

- **`## Stages`** — table: stage | ready-when predicate | action | done | terminal-skip | parked.
- **`## Queries`** — the five query shapes above (ready, claim, reaper, funnel, parked), against the real address.
- **`## Actions`** — *internal stage-actions* (advance rows in-place): readiness = the ready predicate;
  effect = set status + release lease; patch-back = n/a. External pushes stay normal Actions.
- **`## Governance`** — lease duration; the authoritative store is safe for claiming (SQLite txn safe;
  CSV concurrent unsafe).
- **`## Partial rows`** — state the carve-out explicitly: *content columns: `<convention>`; stage columns:
  `NULL` = pending only, never empty-string.*

## The poller (handoff boundary)

The logbook is passive. A poller turns ready-queries into agent dispatches — and that poller is
**skill-creator's job** (or a hook/cron), not this skill's, exactly like the standard "creates the
logbook, not the skill" boundary. The spec gives the poller everything per stage: ready-query + action +
sentinels.

```
loop:
  for stage in <ordered stages>:
    row = atomic_claim(stage)             # ready-query + lease, one statement
    if row: dispatch_agent(stage, row)    # agent works, writes status, releases lease
  if nothing claimed this pass: sleep / exit
```

---

## Worked example (one concrete illustration — do not copy the names)

A literature-review pipeline: sources flow **summarize → assess → verdict**. "Empty stage cell ⇒ an
agent does that stage" is the drive rule. It qualifies (multiple worker agents + a human reviewer; stable
schema; tool-queried; outlives the session) and is a blackboard, not a tracker.

```sql
CREATE TABLE sources (
  id                  INTEGER PRIMARY KEY,
  url                 TEXT    NOT NULL,
  domain_fp           TEXT,                       -- fingerprint for cross-run dedup
  added_at            TEXT    NOT NULL,
  added_by            TEXT    NOT NULL,           -- author (scope is shared)

  summarize_status    TEXT,                       -- NULL=pending | 'done' | 'irrelevant' | 'failed'
  summary             TEXT,                       -- content; MAY be empty when status='done'
  summarize_attempts  INTEGER NOT NULL DEFAULT 0,

  assess_status       TEXT,                       -- NULL=pending | 'done' | 'failed'  (ready iff summarize_status='done')
  relevance           INTEGER,
  credibility         INTEGER,
  assess_attempts     INTEGER NOT NULL DEFAULT 0,

  verdict             TEXT,                       -- NULL=pending | 'include' | 'exclude' | 'needs-human'  (terminal)
  verdict_by          TEXT,
  verdict_at          TEXT,

  claimed_by          TEXT,                       -- shared row-level lease
  claimed_at          TEXT,
  lease_until         TEXT
);
CREATE INDEX idx_summarize_ready ON sources(summarize_status, lease_until);
CREATE INDEX idx_assess_ready    ON sources(assess_status, summarize_status, lease_until);
```

Stages table for its spec:

| Stage | Ready when | Action | Done | Terminal-skip | Parked |
|---|---|---|---|---|---|
| summarize | `summarize_status IS NULL AND summarize_attempts < 3 AND (lease free)` | read URL, write summary | `'done'` | `'irrelevant'` | `'failed'` (3 claims) |
| assess | `assess_status IS NULL AND summarize_status='done' AND assess_attempts < 3 AND (lease free)` | rate relevance+credibility | `'done'` | — | `'failed'` (3 claims) |
| verdict | `verdict IS NULL AND assess_status='done'` | include/exclude/needs-human | non-null | `'exclude'`, `'needs-human'` | — |

Funnel:

```sql
SELECT 'summarize' stage, count(*) n FROM sources WHERE summarize_status IS NULL
UNION ALL SELECT 'assess',  count(*) FROM sources WHERE assess_status IS NULL AND summarize_status='done'
UNION ALL SELECT 'verdict', count(*) FROM sources WHERE verdict IS NULL AND assess_status='done'
UNION ALL SELECT 'skipped', count(*) FROM sources WHERE summarize_status='irrelevant'
UNION ALL SELECT 'parked',  count(*) FROM sources WHERE summarize_status='failed' OR assess_status='failed'
UNION ALL SELECT 'done',    count(*) FROM sources WHERE verdict IS NOT NULL;
```

Every row lands in exactly one bucket (terminal-skips get their own — without the `skipped` line,
`'irrelevant'` rows vanish from the funnel), so the buckets sum to `count(*)` and the funnel doubles
as the completeness partition.

Every footgun is handled: `summary` may be `''` when `summarize_status='done'` (sentinel); the lease +
atomic claim let multiple summarizers run safely (concurrency); `assess` waits on `summarize_status='done'`
(DAG); three claims park a dead URL as `'failed'`, off the queue and surfaced to a human — counted
at claim time, so a summarizer that crashes without ever reporting is bounded by the same counter
and parked by the reaper (poison); `'irrelevant'`/`'exclude'` are done-but-do-not-advance
(terminal outcomes).

(`verdict` doubles as its own sentinel — legitimate here because a *terminal* stage producing a required
enum can never finish *and* be empty. Decision 1's separate-status rule applies to stages whose content
can validly be empty, like `summary`; a pure-enum terminal stage that is never legitimately empty is the
one justified exception, and should be called out as such in the spec. The verdict stage is also
*human-performed* here, which is why it carries no lease, no attempts budget, and no atomic claim — the
per-stage claim/attempts/reaper kit applies to *agent-performed* stages, where workers can race or vanish
mid-claim; an agent-performed verdict would need all three. Call that scoping out in the spec too.)
