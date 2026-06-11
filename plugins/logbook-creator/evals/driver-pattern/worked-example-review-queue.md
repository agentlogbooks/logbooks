# Worked example — a driver logbook (the `reviewed`-column queue)

> **Status:** design fixture for the driver-logbook iteration. Not yet wired into SKILL.md.
> Its job is to (a) prove the "empty cell = pending work" pattern is coherent end-to-end and
> (b) pin down the five decisions the current skill does not yet make, so the eval personas in
> `driver-personas.js` have a concrete target to grade against.

## Scenario

You are building an agentic literature-review pipeline. Sources (URLs) get dropped into a shared
store. Each source must flow through three stages before it can be cited:

1. **summarize** — an agent reads the source and writes a short summary.
2. **assess** — an agent rates relevance + credibility (only meaningful *after* there's a summary).
3. **verdict** — include / exclude / needs-human (only after assessment).

The drive rule is exactly the one in the request: **a stage's cell is empty ⇒ some agent should do
that stage.** `WHERE summarize_status IS NULL` *is* the summarizer's work queue. No external
orchestration list — the table is the todo list, and `GROUP BY stage` is the live burndown.

## First: does this even qualify? (the guard that must not be skipped)

A "driver" framing is **not** a license to skip the logbook-vs-tracker test. This one passes:

- **Multiple contributors** ✓ — several worker agents + a human reviewer write the same rows.
- **Schema-stable** ✓ — every source has the same shape; columns nameable in 30s.
- **Tool-queried, not reread** ✓ — the whole pipeline runs off `WHERE … IS NULL` queries.
- **Outlives the session** ✓ — sources accumulate across many runs.

It is a **blackboard**, not a tracker: agents *pull* empty cells. There are no human assignees, no
due dates, no notifications, no SLAs. The moment those appear (see persona `driver-vs-tracker`),
it's Linear/Jira, not a logbook. Keep that line bright.

---

## The five decisions the current skill does NOT yet make

Everything above reuses the existing flow (scope, location, partitioning, identity, storage). These
five are new — and each is a place the pattern silently breaks if unaddressed.

### 1. Sentinel — "empty" must mean exactly one thing (the killer)

Naive design: trigger on the *content* column — "if `summary` is empty, summarize it." This breaks
the moment a source is legitimately **summarized but yields an empty summary** (paywalled, off-topic,
nothing to extract). That row's `summary` stays empty, so the summarizer re-claims it **forever**.

**Rule:** never trigger on a content column's emptiness. Every stage gets an explicit **status
sentinel** column whose `NULL` means *pending* and whose non-null values are the only "done" signals:

```
summarize_status:  NULL = pending  |  'done'  |  'irrelevant' (terminal-skip)  |  'failed' (parked)
```

`summary` may be empty even when `summarize_status='done'`. The trigger reads the *status*, never the
content. This is the single most important rule the pattern adds, and it directly contradicts the
current skill's "pick one partial-row convention" (Step 3B) — driver logbooks need a carve-out:
*content columns* may use empty-as-missing, but *stage columns* reserve `NULL` for "pending".

### 2. Claiming — concurrent workers must not double-process a row

If three summarizer agents all run `SELECT … WHERE summarize_status IS NULL`, they all grab the same
top row and triple-work it. The queue needs a **claim**: a row-level lease, taken atomically.

**Rule:** claim before working, with an expiring lease so a crashed worker's row is reclaimable:

```sql
-- atomic claim of the next summarize-ready row (SQLite; one statement = one transaction)
UPDATE sources
   SET claimed_by = :worker, claimed_at = :now, lease_until = :now_plus_10min
 WHERE id = (
   SELECT id FROM sources
    WHERE summarize_status IS NULL
      AND (lease_until IS NULL OR lease_until < :now)   -- unclaimed or lease expired
      AND summarize_attempts < 3                        -- not poisoned (decision 4)
    ORDER BY added_at
    LIMIT 1)
RETURNING id, url;                                       -- empty result ⇒ nothing to do
```

This is why **storage choice flips**: the current skill deprioritizes SQLite inside a repo (binary,
review-hostile). But concurrent claiming needs atomic `UPDATE … RETURNING` — **CSV cannot claim
atomically.** So a concurrent driver logbook *requires* SQLite (or a single-writer constraint). That
carve-out belongs in Step 4.

### 3. Stage dependencies — readiness is not a naive null-check

`assess` is meaningless before `summarize` is done. So "assess-ready" is **not** `assess_status IS
NULL` — it's `assess_status IS NULL AND summarize_status='done'`. The stages form a small DAG, and
each stage's queue query must encode its prerequisite.

**Rule:** elicit the stage ordering and emit one readiness query *per stage* that includes the
prerequisite, not a flat "this column is empty".

```sql
-- assess-ready: pending here AND prior stage completed (not skipped/failed)
WHERE assess_status IS NULL AND summarize_status = 'done' AND (lease free) AND assess_attempts < 3
```

### 4. Poison rows — a perpetually-failing item must not starve the queue

A dead URL makes the summarizer error every time. Without a guard it's re-claimed forever — a poison
message that blocks everything behind it.

**Rule:** count attempts; after N, move to a terminal **parked** state that is excluded from the
ready query *and* surfaced to a human. Distinguish transient (retry) from terminal (park):

```
on failure:  summarize_attempts += 1; release lease
             if summarize_attempts >= 3 → summarize_status = 'failed'   (parked, off the queue)
```

### 5. Terminal / non-advancing outcomes

Stage cells carry *outcomes*, not booleans. `summarize_status='irrelevant'` and `verdict='exclude'`
are **done but must not advance** — assess-ready requires `summarize_status='done'` specifically, so
an `'irrelevant'` row never reaches assessment. `verdict` is the absorbing state. Define which values
advance and which absorb, so rows neither get stuck nor wrongly flow downstream.

---

## Artifact 1 — the logbook instance (SQLite schema)

Stored at `~/.local/state/source-review/source-review.sqlite` on the orchestration host (shared
among several worker processes and one human reviewer). SQLite chosen *specifically* for atomic
claiming (decision 2), accepting the loss of plain-text diffability.

```sql
CREATE TABLE sources (
  id                  INTEGER PRIMARY KEY,
  url                 TEXT    NOT NULL,
  domain_fp           TEXT,                       -- fingerprint for cross-run dedup of the same source
  added_at            TEXT    NOT NULL,           -- ISO-8601
  added_by            TEXT    NOT NULL,           -- author (scope is shared)

  -- stage 1: summarize
  summarize_status    TEXT,                       -- NULL=pending | 'done' | 'irrelevant' | 'failed'
  summary             TEXT,                       -- content; MAY be empty when status='done'
  summarize_attempts  INTEGER NOT NULL DEFAULT 0,

  -- stage 2: assess  (ready only when summarize_status='done')
  assess_status       TEXT,                       -- NULL=pending | 'done' | 'failed'
  relevance           INTEGER,                    -- 0..5
  credibility         INTEGER,                    -- 0..5
  assess_attempts     INTEGER NOT NULL DEFAULT 0,

  -- stage 3: verdict (ready only when assess_status='done'); terminal
  verdict             TEXT,                       -- NULL=pending | 'include' | 'exclude' | 'needs-human'
  verdict_by          TEXT,
  verdict_at          TEXT,

  -- row-level lease (a row is worked at exactly one stage at a time, so one lease suffices)
  claimed_by          TEXT,
  claimed_at          TEXT,
  lease_until         TEXT                        -- ISO-8601; NULL or past = free to claim
);

CREATE INDEX idx_summarize_ready ON sources(summarize_status, lease_until);
CREATE INDEX idx_assess_ready    ON sources(assess_status, summarize_status, lease_until);
CREATE INDEX idx_verdict_ready   ON sources(verdict, assess_status, lease_until);
CREATE INDEX idx_domain_fp       ON sources(domain_fp);
```

## Artifact 2 — the spec (`source-review.logbook.md`)

Follows the skill's spec template, **extended** with the three driver-specific pieces marked
`[DRIVER]`. Everything unmarked is the existing template.

```markdown
# Logbook: source-review

A driver logbook that runs sources through summarize → assess → verdict. Empty stage-status cells
are the work queue; worker agents and one human reviewer advance rows. Blackboard, not a tracker.

## Address
/Users/<you>/.local/state/source-review/source-review.sqlite  (table: sources)
When the user moves this file, update the address here.

## Storage
SQLite — chosen for ATOMIC CLAIMING (UPDATE … RETURNING). A concurrent driver queue cannot use CSV
because plain files can't claim a row atomically. Diffability is sacrificed deliberately.

## Schema
(see the three stage-column groups in the DDL; each stage = <stage>_status + content + _attempts)

## Identity
Auto-increment `id` per row. `domain_fp` (hash of the canonicalized URL) dedups the same source
across ingest runs — check it before inserting.

## Partial rows
CONTENT columns (`summary`, `relevance`, …): empty = genuinely no value.
STAGE columns (`*_status`, `verdict`): NULL is RESERVED for "pending" — never write empty-string to a
stage column. (This is the driver carve-out from the normal one-convention rule.)

## [DRIVER] Stages
| Stage | Trigger (ready query predicate) | Action | Done | Terminal-skip | Parked |
|---|---|---|---|---|---|
| summarize | `summarize_status IS NULL` | read URL, write summary | `'done'` | `'irrelevant'` | `'failed'` (3 tries) |
| assess | `assess_status IS NULL AND summarize_status='done'` | rate relevance+credibility | `'done'` | — | `'failed'` (3 tries) |
| verdict | `verdict IS NULL AND assess_status='done'` | include/exclude/needs-human | non-null | `'exclude'`, `'needs-human'` | — |

Each stage: claim (atomic, with lease) → do work → set `<stage>_status` + release lease. On error,
increment `<stage>_attempts`, release lease; at attempts ≥ 3 set status `'failed'`.

## Queries
### summarize-ready (the summarizer's queue)
SELECT id, url FROM sources
 WHERE summarize_status IS NULL AND (lease_until IS NULL OR lease_until < :now)
   AND summarize_attempts < 3 ORDER BY added_at;

### atomic claim (next summarize-ready row)
UPDATE sources SET claimed_by=:w, claimed_at=:now, lease_until=:t
 WHERE id=(SELECT id FROM sources WHERE summarize_status IS NULL
            AND (lease_until IS NULL OR lease_until<:now) AND summarize_attempts<3
            ORDER BY added_at LIMIT 1) RETURNING id, url;

### assess-ready / verdict-ready
… assess_status IS NULL AND summarize_status='done' …
… verdict       IS NULL AND assess_status='done'    …

### [DRIVER] funnel (live burndown — the payoff of the pattern)
SELECT 'summarize' stage, count(*) n FROM sources WHERE summarize_status IS NULL
UNION ALL SELECT 'assess',  count(*) FROM sources WHERE assess_status IS NULL AND summarize_status='done'
UNION ALL SELECT 'verdict', count(*) FROM sources WHERE verdict IS NULL AND assess_status='done'
UNION ALL SELECT 'parked',  count(*) FROM sources WHERE summarize_status='failed' OR assess_status='failed'
UNION ALL SELECT 'done',    count(*) FROM sources WHERE verdict IS NOT NULL;

### parked rows needing a human (poison dead-letter)
SELECT id, url, summarize_attempts, assess_attempts FROM sources
 WHERE summarize_status='failed' OR assess_status='failed' OR verdict='needs-human';

## Validation
A row is "fully processed" iff `verdict IS NOT NULL`. A stuck row = `lease_until < :now` while a
stage is still pending (worker crashed mid-claim) — it is auto-reclaimable. Invariant check:
no row may have `assess_status='done'` while `summarize_status` is NULL or 'failed'.

## [DRIVER] Actions  (internal stage-actions vs external pushes)
These actions ADVANCE rows inside the logbook; they don't push to an external system.
### summarize / assess / verdict
- Readiness check: the stage's ready-query predicate above.
- Dry-run: run the SELECT (no claim) to preview the queue.
- Effect: sets the stage's status + content columns; releases the lease.
- Patch-back: n/a (the logbook is authoritative; no external target).
(If an external push is later added — e.g. export included sources to a bibliography — it becomes a
normal external Action with a patch-back column.)

## Governance
- Access: any worker process may claim+advance; the human sets `verdict='needs-human'` rows.
- Concurrency: row-level lease; lease_until expiry = 10 min. SQLite transaction = last-write-wins safe.
- Lifetime: indefinite. Sunset: archive sources with a verdict older than 1 year to `archive/`.
```

---

## The poller (the handoff boundary)

The logbook is passive. A poller drives it — and that poller is **skill-creator's / a hook's job**,
not this skill's, exactly like the existing "creates the logbook, not the skill" boundary. The spec
gives the poller everything it needs (ready query + action + sentinels per stage):

```
loop:
  for stage in [summarize, assess, verdict]:
    row = atomic_claim(stage)          # ready-query + lease, one statement
    if row: dispatch_agent(stage, row) # agent does work, writes status, releases lease
  if no rows claimed this pass: sleep / exit
```

That is the whole pattern: **the schema is a state machine; emptiness is the transition trigger; the
spec emits one ready-query + action per stage; a thin poller turns queries into agent dispatches.**
```
