#!/usr/bin/env python3
"""
The liveness hole, demonstrated — and closed.   python3 liveness_demo.py  (exit 0 = both proofs hold)

Scenario: one row ("hooli.com"), techstack stage, and a worker fleet that CRASHES on it every
time (spot-instance kill: the worker claims the row, dies before doing any work, reports nothing).
Time is a LOGICAL clock (a minute counter from a fixed base) — deterministic, no wall clock.

RED  (error-time counting, the classic design): every claim sets a lease; the crash means the
     error branch never runs, so <stage>_attempts never moves; the lease expires; the row is
     silently reclaimed. We run 12 cycles: 12 claims, attempts still 0, row still pending — and
     the full snapshot-invariant audit PASSES at every single step. The starvation loop is
     structurally invisible to any point-in-time audit. That is a liveness failure, not a safety
     failure: each photo is healthy; only the film shows the row never finishes.

GREEN (claim-time counting + reaper): the atomic claim itself increments <stage>_attempts, so a
     crash still counts; and the RECLAIM PATH parks the row once attempts >= N (a reaper) —
     parking no longer depends on a worker surviving to its error handler. After exactly N=3
     claims the row is parked, surfaced by the dead-letter query, and the liveness property
     becomes a checkable safety invariant: "no pending row has attempts >= N".
"""
import os, sqlite3, sys
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = datetime(2026, 6, 11, 12, 0, 0)          # fixed logical base; never the wall clock
LEASE_MIN = 15
N = 3

def iso(t_min):
    return (BASE + timedelta(minutes=t_min)).strftime("%Y-%m-%dT%H:%M:%SZ")

# The snapshot-invariant audit (same checks as audit.py, parameterized by logical :now).
def snapshot_invariants(con, now):
    checks = {
      "C1 partition total": f"""
        SELECT count(*) FROM companies WHERE NOT (
             firmographics_status='failed' OR techstack_status='failed' OR contacts_status='failed'
          OR fit_score IS NOT NULL
          OR (lease_until IS NOT NULL AND lease_until > '{now}')
          OR firmographics_status IS NULL
          OR (techstack_status IS NULL AND firmographics_status='done')
          OR (contacts_status IS NULL AND techstack_status IN ('done','none-detected'))
          OR (fit_score IS NULL AND contacts_status IN ('done','no-contact')))""",
      "C2 DAG monotonic": """
        SELECT count(*) FROM companies
         WHERE (techstack_status IS NOT NULL AND (firmographics_status IS NULL OR firmographics_status<>'done'))
            OR (contacts_status  IS NOT NULL AND (techstack_status IS NULL OR techstack_status NOT IN ('done','none-detected')))
            OR (fit_score        IS NOT NULL AND (contacts_status  IS NULL OR contacts_status  NOT IN ('done','no-contact')))""",
      "C3 sentinel integrity":
        "SELECT count(*) FROM companies WHERE firmographics_status='' OR techstack_status='' OR contacts_status=''",
      # Lease-aware under claim-time counting: attempts can legitimately equal N while the Nth
      # claim is still in flight (lease live). A violation is an exhausted row AT REST — pending,
      # past the cap, lease expired/absent — i.e. exactly what the reaper must have parked.
      "C5 no exhausted row at rest": f"""
        SELECT count(*) FROM companies
         WHERE (lease_until IS NULL OR lease_until <= '{now}')
           AND (   (firmographics_status IS NULL AND firmographics_attempts >= {N})
                OR (techstack_status     IS NULL AND techstack_attempts     >= {N})
                OR (contacts_status      IS NULL AND contacts_attempts      >= {N}))""",
      "C6 no leaked claim":
        f"SELECT count(*) FROM companies WHERE claimed_by IS NOT NULL AND lease_until <= '{now}'",
    }
    return {name: con.execute(q).fetchone()[0] for name, q in checks.items()}

def fresh_db():
    con = sqlite3.connect(":memory:")
    con.executescript(open(os.path.join(HERE, "schema.driver.sql")).read())
    con.execute("""INSERT INTO companies(id,domain,domain_fp,added_at,added_by,
                   firmographics_status,industry,employee_count,hq_country)
                   VALUES(1,'hooli.com','hooli',?, 'seed-bot','done','Platform',6000,'US')""", (iso(0),))
    con.commit()
    return con

READY = "techstack_status IS NULL AND firmographics_status='done'"

def claim(con, t_min, count_at_claim):
    """Atomic claim of the techstack stage. count_at_claim toggles RED vs GREEN counting."""
    bump = ", techstack_attempts = techstack_attempts + 1" if count_at_claim else ""
    row = con.execute(f"""
      UPDATE companies SET claimed_by='spot-worker', claimed_at=?, lease_until=?{bump}
       WHERE id = (SELECT id FROM companies
                    WHERE {READY} AND techstack_attempts < {N}
                      AND (lease_until IS NULL OR lease_until < ?)
                    LIMIT 1)
      RETURNING id, techstack_attempts""", (iso(t_min), iso(t_min + LEASE_MIN), iso(t_min))).fetchone()
    con.commit()
    return row

def reaper(con, t_min):
    """The reclaim path parks exhausted rows — parking does not depend on a worker reporting."""
    n = con.execute(f"""
      UPDATE companies SET techstack_status='failed', claimed_by=NULL, claimed_at=NULL, lease_until=NULL
       WHERE techstack_status IS NULL AND techstack_attempts >= {N}
         AND (lease_until IS NULL OR lease_until < ?)""", (iso(t_min),)).rowcount
    con.commit()
    return n

def run(mode):
    """mode 'red' = error-time counting, no reaper; mode 'green' = claim-time counting + reaper."""
    con = fresh_db()
    claims_made, audits_passed, audits_run = 0, 0, 0
    parked_at_claim = None
    print(f"\n--- {mode.upper()}: {'error-time counting, no reaper' if mode=='red' else 'claim-time counting + reaper'} ---")
    print(f"{'cycle':>5} {'t':>5}  {'claimed?':<9}{'attempts':>8}  {'status':<8} snapshot-audit")
    t = 0
    for cycle in range(1, 13):
        t += LEASE_MIN + 5                       # logical time passes; any lease has expired
        if mode == "green":
            reaper(con, t)
        row = claim(con, t, count_at_claim=(mode == "green"))
        if row:
            claims_made += 1                     # the worker now CRASHES: writes nothing, reports nothing
        att, status = con.execute("SELECT techstack_attempts, techstack_status FROM companies").fetchone()
        inv = snapshot_invariants(con, iso(t + 1))   # audit at a moment the lease is still live
        ok = all(v == 0 for v in inv.values())
        audits_run += 1; audits_passed += ok
        print(f"{cycle:>5} {t:>4}m  {'claim #'+str(claims_made) if row else 'no claim':<9}{att:>8}  {str(status):<8} {'PASS' if ok else 'FAIL: '+str(inv)}")
        if status == 'failed' and parked_at_claim is None:
            parked_at_claim = claims_made
            break
    dead = con.execute("SELECT domain, techstack_attempts FROM companies WHERE techstack_status='failed'").fetchall()
    con.close()
    return dict(claims=claims_made, attempts=att, status=status,
                audits_passed=audits_passed, audits_run=audits_run,
                parked_at_claim=parked_at_claim, dead_letter=dead)

if __name__ == "__main__":
    print("=== LIVENESS DEMO: one row, a worker fleet that always crashes on it ===")
    red = run("red")
    green = run("green")

    print("\n=== VERDICT ===")
    print(f"RED   : {red['claims']} claims, attempts still {red['attempts']}, status {red['status']}, "
          f"snapshot audit passed {red['audits_passed']}/{red['audits_run']} times")
    print(f"        -> the row would loop forever; every snapshot looks healthy. UNDETECTABLE starvation.")
    print(f"GREEN : parked after exactly {green['parked_at_claim']} claims (attempts={green['attempts']}, "
          f"status={green['status']}); dead-letter: {green['dead_letter']}")
    print(f"        -> liveness is now the safety invariant C5: no pending row with attempts >= {N}.")

    failures = []
    if not (red["claims"] >= 10 and red["attempts"] == 0 and red["status"] is None):
        failures.append("RED did not exhibit the unbounded crash-reclaim loop")
    if red["audits_passed"] != red["audits_run"]:
        failures.append("RED audit FAILED somewhere -- the hole would be snapshot-detectable, contradiction")
    if green["audits_passed"] != green["audits_run"]:
        failures.append("GREEN audit FAILED somewhere -- the lease-aware C5 should hold at every audited step")
    if not (green["parked_at_claim"] == N and green["status"] == "failed" and green["attempts"] == N):
        failures.append(f"GREEN did not park at exactly N={N} claims")
    if not green["dead_letter"]:
        failures.append("GREEN parked row missing from dead-letter")
    if failures:
        print("\nRESULT: FAIL -- " + "; ".join(failures)); sys.exit(1)
    print("\nRESULT: PASS -- the hole is real and snapshot-invisible (RED); claim-time counting + reaper close it (GREEN).")
