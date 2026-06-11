# Logbook spec — company-enrichment driver

Produced by following `logbook-creator` SKILL.md (Steps 1–5, driver variant — Step 2.5).
This is the *logbook* artifact; the *poller/skill* that dispatches workers is skill-creator's job
(handoff boundary, below).

## Step 1–2 trace (why this shape)

- **Motivation:** *Driver / work-queue* — the schema is the todo list; an empty `<phase>_status` cell
  is the trigger for a worker to do that phase. Four phases **accumulate data** into each row:
  `firmographics → techstack → contacts → score`.
- **Qualifies (three of four):** multiple worker agents + a human reviewing parked rows; stable schema;
  tool-queried (ready/funnel/dead-letter); outlives any one session. ✓
- **Tracker pre-check (Step 2.5):** no per-person assignment, no due dates, no notifications, no staleness
  SLAs — workers *pull* empty cells. It is a **blackboard, not a tracker**; the Jira/Linear redirect does
  not fire. ✓
- **Architecture (2.4):** single record type (`companies`); the driver dimension is orthogonal.

## The five driver decisions (Step 2.5)

| # | Decision | Resolution here |
|---|----------|-----------------|
| 1 | **Sentinel** | One `<phase>_status` column per phase. `NULL`=pending only. `techstack`/`contacts` can finish *successfully empty* (`none-detected`/`no-contact`) — exactly why a content column can't be the trigger. `fit_score` is the justified pure-enum terminal exception (a number that can never finish empty). |
| 2 | **Concurrency** | Many enrichment workers run at once → `claimed_by`/`claimed_at`/`lease_until` lease; atomic `UPDATE … WHERE id=(SELECT … LIMIT 1) RETURNING`. Forces **SQLite** (CSV can't claim atomically — Step 4). |
| 3 | **Stage DAG** | Linear: each phase's ready-query carries its prerequisite (`techstack` ready iff `firmographics_status='done'`; `contacts` iff `techstack_status IN ('done','none-detected')`; `score` iff `contacts_status IN ('done','no-contact')`). The advancing set is wider than `'done'`. |
| 4 | **Poison rows** | `<phase>_attempts` counter; after `N=3` the phase status flips to `'failed'` (parked, off the ready-query) and is surfaced by the dead-letter query. |
| 5 | **Terminal outcomes** | `'done'` and the legit-empty skips (`none-detected`, `no-contact`) **advance**; `'failed'` **absorbs**; `fit_score` non-null is the terminal done. Named, not boolean. |

## Address

`sqlite:///Users/.../data-completeness-demo/driver.db` → table `companies`.
Schema: `schema.driver.sql` (live queue). If repo visibility matters, commit only an exported snapshot
projection, not the live `.db` (Step 4).

## Stages

| Stage | Ready when | Action | Done | Terminal-skip (advances) | Parked (absorbs) |
|---|---|---|---|---|---|
| firmographics | `firmographics_status IS NULL` | fetch industry/size/HQ | `'done'` (3 fields) | — | `'failed'` (3 tries) |
| techstack | `techstack_status IS NULL AND firmographics_status='done'` | detect cms/analytics/cloud | `'done'` (≥1 signal) | `'none-detected'` (content empty) | `'failed'` (3 tries) |
| contacts | `contacts_status IS NULL AND techstack_status IN ('done','none-detected')` | find primary email | `'done'` (email) | `'no-contact'` | `'failed'` (3 tries) |
| score | `fit_score IS NULL AND contacts_status IN ('done','no-contact')` | compute fit_score | `fit_score` non-null | — | — |

## Queries (`completeness-audit.sql`)

- **ready-query** (per stage): `… WHERE <ready> AND <stage>_attempts < 3 AND (lease_until IS NULL OR lease_until < :now)`
- **atomic claim**: `UPDATE companies SET claimed_by=:w, lease_until=:now+lease WHERE id=(SELECT id … LIMIT 1) RETURNING …`
- **funnel / partition** (the data-completeness burndown): one bucket per row → `complete | in_flight | parked | pending_<stage>`; must sum to total with zero `ORPHAN`.
- **dead-letter** (parked, for a human): `WHERE <stage>_status='failed'`.

## Actions

Internal stage-actions advance rows in place: readiness = the stage ready predicate; effect = set
`<stage>_status` + write content + release lease; patch-back = n/a. No external pushes.

## Governance

Lease = 15 min. SQLite transaction makes the claim atomic (safe for concurrent workers). `NULL`
sentinel + attempts counter make every row classifiable, so **completeness is a query, not a guess**.

## Partial rows

Content columns: `NULL` = not-yet / legitimately-absent (distinguished by the phase status).
**Status columns: `NULL` = pending *only*, never empty-string** (Step 2.5 carve-out).

## Handoff boundary

The logbook is passive. A poller turns each stage's ready-query into agent dispatches —
**skill-creator's job** (or a hook/cron), not this skill's. The spec above gives the poller everything
per stage: ready-query + action + sentinels.

## Data-completeness result

`python3 audit.py` → all 9 invariants PASS; partition `9 complete + 1 in_flight + 2 parked = 12`.
The naive contrast schema (`schema.naive.sql`, no sentinels/attempts) can only see `8 complete / 4
pending`, misclassifying the two legit-empty rows as pending and the two poison rows as in-progress —
completeness is **unprovable** without the driver pattern's status columns.
