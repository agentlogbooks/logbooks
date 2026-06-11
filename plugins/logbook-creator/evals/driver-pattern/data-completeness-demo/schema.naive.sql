-- Anti-pattern schema (the thing logbook-creator Step 2.5 tells you NOT to build).
-- Same four phases, same content columns -- but NO status sentinels, NO attempts
-- counters, NO lease. "Pending" is inferred from a CONTENT column being NULL.
-- This file exists only so the completeness audit can show what breaks.

CREATE TABLE companies_naive (
  id              INTEGER PRIMARY KEY,
  domain          TEXT    NOT NULL UNIQUE,
  added_at        TEXT    NOT NULL,

  -- Phase 1: firmographics -- "pending" inferred as: industry IS NULL
  industry        TEXT,
  employee_count  INTEGER,
  hq_country      TEXT,

  -- Phase 2: techstack -- "pending" inferred as: cms IS NULL AND analytics IS NULL AND cloud IS NULL
  cms             TEXT,
  analytics       TEXT,
  cloud           TEXT,

  -- Phase 3: contacts -- "pending" inferred as: primary_email IS NULL
  primary_email   TEXT,
  contact_name    TEXT,

  -- Phase 4: score -- "pending" inferred as: fit_score IS NULL
  fit_score       INTEGER
);
-- Footguns baked in:
--  * A company with NO detectable tech leaves cms/analytics/cloud NULL -> looks pending forever.
--  * A dead/parked domain whose firmographics fetch always errors -> re-fetched forever, never terminal.
--  * No way to compute a clean {pending | parked | complete} partition: empty content is ambiguous.
