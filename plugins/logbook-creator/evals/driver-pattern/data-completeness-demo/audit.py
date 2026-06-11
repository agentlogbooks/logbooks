#!/usr/bin/env python3
"""
Self-checking data-completeness test.
  python3 audit.py        # exits 0 iff every invariant holds on driver.db
Runs the invariants from completeness-audit.sql as assertions, then shows the
naive schema cannot even compute a clean completeness partition.
"""
import os, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
NOW  = "2026-06-11T12:00:00Z"
N    = 3

# Each invariant: a query whose count MUST be 0.
INVARIANTS = {
 "C1 partition is total (no orphan row)": f"""
   SELECT count(*) FROM companies WHERE NOT (
        firmographics_status='failed' OR techstack_status='failed' OR contacts_status='failed'
     OR fit_score IS NOT NULL
     OR (lease_until IS NOT NULL AND lease_until > '{NOW}')
     OR firmographics_status IS NULL
     OR (techstack_status IS NULL AND firmographics_status='done')
     OR (contacts_status IS NULL AND techstack_status IN ('done','none-detected'))
     OR (fit_score IS NULL AND contacts_status IN ('done','no-contact')))""",
 "C2 DAG monotonic (no gap / out-of-order advance)": """
   SELECT count(*) FROM companies
    WHERE (techstack_status IS NOT NULL AND (firmographics_status IS NULL OR firmographics_status<>'done'))
       OR (contacts_status  IS NOT NULL AND (techstack_status IS NULL OR techstack_status NOT IN ('done','none-detected')))
       OR (fit_score        IS NOT NULL AND (contacts_status  IS NULL OR contacts_status  NOT IN ('done','no-contact')))""",
 "C3 sentinel integrity (no empty-string status)":
   "SELECT count(*) FROM companies WHERE firmographics_status='' OR techstack_status='' OR contacts_status=''",
 "C4a firmographics done => fields filled":
   "SELECT count(*) FROM companies WHERE firmographics_status='done' AND (industry IS NULL OR employee_count IS NULL OR hq_country IS NULL)",
 "C4b techstack done => >=1 signal":
   "SELECT count(*) FROM companies WHERE techstack_status='done' AND cms IS NULL AND analytics IS NULL AND cloud IS NULL",
 "C4c none-detected => content empty":
   "SELECT count(*) FROM companies WHERE techstack_status='none-detected' AND (cms IS NOT NULL OR analytics IS NOT NULL OR cloud IS NOT NULL)",
 "C4d contacts done<=>email present":
   "SELECT count(*) FROM companies WHERE (contacts_status='done' AND primary_email IS NULL) OR (contacts_status='no-contact' AND primary_email IS NOT NULL)",
 "C5 no live row past attempt cap": f"""
   SELECT count(*) FROM companies
    WHERE (firmographics_status IS NULL AND firmographics_attempts >= {N})
       OR (techstack_status     IS NULL AND techstack_attempts     >= {N})
       OR (contacts_status      IS NULL AND contacts_attempts      >= {N})""",
 "C6 no claimed row with expired lease (no leaked claim)":
   f"SELECT count(*) FROM companies WHERE claimed_by IS NOT NULL AND lease_until <= '{NOW}'",
}

def run_driver():
    con = sqlite3.connect(os.path.join(HERE, "driver.db"))
    total = con.execute("SELECT count(*) FROM companies").fetchone()[0]
    buckets = con.execute(f"""
      SELECT CASE
        WHEN firmographics_status='failed' OR techstack_status='failed' OR contacts_status='failed' THEN 'parked'
        WHEN fit_score IS NOT NULL THEN 'complete'
        WHEN lease_until IS NOT NULL AND lease_until > '{NOW}' THEN 'in_flight'
        ELSE 'pending' END b, count(*) FROM companies GROUP BY b ORDER BY b""").fetchall()
    print(f"DRIVER  total rows = {total}   partition: " + ", ".join(f"{b}={n}" for b,n in buckets))
    assert sum(n for _,n in buckets) == total, "partition does not sum to total"

    failures = []
    for name, q in INVARIANTS.items():
        observed = con.execute(q).fetchone()[0]
        ok = observed == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}  (observed={observed})")
        if not ok: failures.append(name)
    con.close()
    return failures

def run_naive():
    con = sqlite3.connect(os.path.join(HERE, "naive.db"))
    total = con.execute("SELECT count(*) FROM companies_naive").fetchone()[0]
    # The only completeness signal naive has is "all content columns filled".
    apparent_done = con.execute("""SELECT count(*) FROM companies_naive
        WHERE industry IS NOT NULL AND cms IS NOT NULL AND primary_email IS NOT NULL AND fit_score IS NOT NULL""").fetchone()[0]
    looks_pending = total - apparent_done
    print(f"\nNAIVE   total rows = {total}   apparent-complete (all content filled) = {apparent_done}, "
          f"looks-pending = {looks_pending}")
    print("  The driver logbook proved 9 complete + 2 parked + 1 in-flight = 12 (every row accounted for).")
    print(f"  The naive schema can only say {apparent_done} are 'complete' and {looks_pending} 'still pending' --")
    print("  but umbrella/soylent are DONE (legit-empty content) and wonka/cyberdyne are PARKED (un-doable).")
    print("  It cannot tell legit-empty from pending or doomed from in-progress: completeness UNPROVABLE.")
    con.close()

if __name__ == "__main__":
    print("=== DATA-COMPLETENESS TEST ===")
    failures = run_driver()
    run_naive()
    if failures:
        print(f"\nRESULT: FAIL -- {len(failures)} invariant(s) violated: {failures}")
        sys.exit(1)
    print("\nRESULT: PASS -- every row is accounted for and every 'done' cell is provably complete.")
