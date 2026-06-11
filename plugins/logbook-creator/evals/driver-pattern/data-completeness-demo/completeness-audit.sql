-- =============================================================================
-- DATA-COMPLETENESS AUDIT for the company-enrichment driver logbook.
-- Run:  sqlite3 driver.db < completeness-audit.sql
-- Every "verdict" column must read PASS. The clock is the harness's fixed NOW.
-- The same invariants are UNPROVABLE on naive.db (no status sentinels to read).
-- =============================================================================
.mode column
.headers on
.parameter set @now '2026-06-11T12:00:00Z'

-- ---- 0. Bucket partition: every row in exactly one state ---------------------
-- Priority CASE assigns ONE bucket; ORPHAN catches any row no rule classifies.
WITH b AS (
  SELECT id,
    CASE
      WHEN firmographics_status='failed' OR techstack_status='failed' OR contacts_status='failed' THEN 'parked'
      WHEN fit_score IS NOT NULL THEN 'complete'
      WHEN lease_until IS NOT NULL AND lease_until > '2026-06-11T12:00:00Z' THEN 'in_flight'
      WHEN firmographics_status IS NULL THEN 'pending_firmographics'
      WHEN techstack_status IS NULL AND firmographics_status='done' THEN 'pending_techstack'
      WHEN contacts_status IS NULL AND techstack_status IN ('done','none-detected') THEN 'pending_contacts'
      WHEN fit_score IS NULL AND contacts_status IN ('done','no-contact') THEN 'pending_score'
      ELSE 'ORPHAN'
    END bucket
  FROM companies)
SELECT bucket, count(*) n FROM b GROUP BY bucket ORDER BY bucket;

-- ---- The invariants (each observed count MUST be 0) --------------------------
WITH checks AS (
  -- C1: partition is total -- no row falls outside every bucket
  SELECT 'C1 no orphan rows (partition total)' chk, count(*) observed FROM companies
   WHERE NOT (
        firmographics_status='failed' OR techstack_status='failed' OR contacts_status='failed'
     OR fit_score IS NOT NULL
     OR (lease_until IS NOT NULL AND lease_until > '2026-06-11T12:00:00Z')
     OR firmographics_status IS NULL
     OR (techstack_status IS NULL AND firmographics_status='done')
     OR (contacts_status IS NULL AND techstack_status IN ('done','none-detected'))
     OR (fit_score IS NULL AND contacts_status IN ('done','no-contact')) )

  -- C2: DAG monotonicity -- no stage advanced unless its prerequisite is in the advancing set
  UNION ALL SELECT 'C2 no out-of-order / gap advances', count(*) FROM companies
   WHERE (techstack_status IS NOT NULL AND (firmographics_status IS NULL OR firmographics_status<>'done'))
      OR (contacts_status  IS NOT NULL AND (techstack_status IS NULL OR techstack_status NOT IN ('done','none-detected')))
      OR (fit_score        IS NOT NULL AND (contacts_status  IS NULL OR contacts_status  NOT IN ('done','no-contact')))

  -- C3: sentinel integrity -- a status column never holds empty string (=='' is indistinguishable from pending)
  UNION ALL SELECT 'C3 no empty-string status (sentinel)', count(*) FROM companies
   WHERE firmographics_status='' OR techstack_status='' OR contacts_status=''

  -- C4a: firmographics done => all required content present
  UNION ALL SELECT 'C4a firmographics done => fields filled', count(*) FROM companies
   WHERE firmographics_status='done' AND (industry IS NULL OR employee_count IS NULL OR hq_country IS NULL)
  -- C4b: techstack done => >=1 signal present
  UNION ALL SELECT 'C4b techstack done => >=1 signal', count(*) FROM companies
   WHERE techstack_status='done' AND cms IS NULL AND analytics IS NULL AND cloud IS NULL
  -- C4c: techstack none-detected => content legitimately empty (the sentinel pays off)
  UNION ALL SELECT 'C4c none-detected => content empty', count(*) FROM companies
   WHERE techstack_status='none-detected' AND (cms IS NOT NULL OR analytics IS NOT NULL OR cloud IS NOT NULL)
  -- C4d: contacts done => email present ; no-contact => email absent
  UNION ALL SELECT 'C4d contacts done<=>email present', count(*) FROM companies
   WHERE (contacts_status='done' AND primary_email IS NULL)
      OR (contacts_status='no-contact' AND primary_email IS NOT NULL)

  -- C5: poison accounting -- no still-pending row past the attempt cap (it must be parked, not NULL)
  UNION ALL SELECT 'C5 no live row past attempt cap', count(*) FROM companies
   WHERE (firmographics_status IS NULL AND firmographics_attempts >= 3)
      OR (techstack_status     IS NULL AND techstack_attempts     >= 3)
      OR (contacts_status      IS NULL AND contacts_attempts      >= 3)

  -- C6: no leaked claim -- a claimed row with an expired lease is a lost row (should be released/reclaimed)
  UNION ALL SELECT 'C6 no claimed row with expired lease', count(*) FROM companies
   WHERE claimed_by IS NOT NULL AND lease_until <= '2026-06-11T12:00:00Z'
)
SELECT chk, observed, CASE WHEN observed=0 THEN 'PASS' ELSE 'FAIL' END verdict FROM checks;

-- ---- Dead-letter: parked rows surfaced for a human (Decision 4) --------------
SELECT 'firmographics' stage, domain, firmographics_attempts attempts FROM companies WHERE firmographics_status='failed'
UNION ALL SELECT 'techstack', domain, techstack_attempts FROM companies WHERE techstack_status='failed'
UNION ALL SELECT 'contacts',  domain, contacts_attempts  FROM companies WHERE contacts_status='failed';
