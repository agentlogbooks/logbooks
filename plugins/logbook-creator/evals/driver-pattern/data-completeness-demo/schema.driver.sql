-- Driver (work-queue) logbook produced by following logbook-creator Step 2.5.
-- Domain: company enrichment. Four phases ACCUMULATE data into each row:
--   firmographics -> techstack -> contacts -> score
-- Drive rule: an empty <phase>_status cell is the trigger for a worker to do that phase.
-- Every footgun (sentinel / concurrency / DAG / poison / terminal outcomes) is handled.
-- <phase>_attempts counts CLAIMS, incremented inside the atomic claim itself (not in the worker's
-- error branch): a worker that crashes without reporting still counts, and the reclaim path parks
-- exhausted rows (reaper) -- closing the claim->crash->reclaim liveness hole. See liveness_demo.py.

CREATE TABLE companies (
  id                     INTEGER PRIMARY KEY,
  domain                 TEXT    NOT NULL UNIQUE,
  domain_fp              TEXT,                              -- dedup fingerprint (cross-run)
  added_at               TEXT    NOT NULL,
  added_by               TEXT    NOT NULL,                  -- author (scope is shared)

  -- Phase 1: firmographics  (advancing set: {'done'} ; absorbing: {'failed'})
  firmographics_status   TEXT,                              -- NULL=pending | 'done' | 'failed'
  industry               TEXT,                              -- content; REQUIRED when status='done'
  employee_count         INTEGER,                           -- content; REQUIRED when status='done'
  hq_country             TEXT,                              -- content; REQUIRED when status='done'
  firmographics_attempts INTEGER NOT NULL DEFAULT 0,

  -- Phase 2: techstack  (ready iff firmographics_status='done')
  --   advancing set: {'done','none-detected'} ; absorbing: {'failed'}
  --   'none-detected' is the LEGITIMATELY-EMPTY case: status advances, content stays NULL.
  techstack_status       TEXT,                              -- NULL=pending | 'done' | 'none-detected' | 'failed'
  cms                    TEXT,                              -- content; may be NULL when status='none-detected'
  analytics              TEXT,
  cloud                  TEXT,
  techstack_attempts     INTEGER NOT NULL DEFAULT 0,

  -- Phase 3: contacts  (ready iff techstack_status IN ('done','none-detected'))
  --   advancing set: {'done','no-contact'} ; absorbing: {'failed'}
  contacts_status        TEXT,                              -- NULL=pending | 'done' | 'no-contact' | 'failed'
  primary_email          TEXT,                              -- content; REQUIRED when status='done'
  contact_name           TEXT,
  contacts_attempts      INTEGER NOT NULL DEFAULT 0,

  -- Phase 4: score  (terminal; ready iff contacts_status IN ('done','no-contact'))
  --   fit_score doubles as its own sentinel: a terminal enum/number that can never
  --   legitimately finish empty (Decision 1's justified exception).
  fit_score              INTEGER,                           -- NULL=pending | integer = done (terminal)
  scored_at              TEXT,

  -- Shared row-level lease (Decision 2 — concurrent workers)
  claimed_by             TEXT,
  claimed_at             TEXT,
  lease_until            TEXT                               -- ISO-8601; row reclaimable once past
);

-- Ready-query indexes (one per stage; carries the prerequisite column)
CREATE INDEX idx_firmographics_ready ON companies(firmographics_status, lease_until);
CREATE INDEX idx_techstack_ready     ON companies(techstack_status, firmographics_status, lease_until);
CREATE INDEX idx_contacts_ready      ON companies(contacts_status, techstack_status, lease_until);
CREATE INDEX idx_score_ready         ON companies(fit_score, contacts_status, lease_until);
