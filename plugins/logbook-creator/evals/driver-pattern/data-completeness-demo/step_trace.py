#!/usr/bin/env python3
"""
Append-only RUN-TRACE projection: rebuild the queue step by step, recording a
partition snapshot after each work unit into driver.history.jsonl.

This is the second of logbook-creator's three projection roles (run-trace): an
append-only event log that PRESERVES the trajectory a patch-in-place ledger
overwrites. render.py reads it to draw the burndown. Without it there is no
"progress over time" -- a single snapshot of the live ledger has no history.

Deterministic: it reuses harness.py's exact claim/advance logic against the same
fixed "world", so the same inputs always produce the same frames. It rebuilds
driver.db to the identical fixpoint harness.py produces, plus the history file.

    python3 step_trace.py        # -> driver.db (at fixpoint) + driver.history.jsonl
"""
import os, sqlite3, json
import harness
from harness import claim_next, do_stage, STAGES, WORLD, MID, NOW, LEASE  # untouched demo logic

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, "driver.history.jsonl")

def snapshot(con, step, label):
    """A partition snapshot -- same bucket precedence as audit.py / render.py."""
    rows = con.execute(
        "SELECT firmographics_status,techstack_status,contacts_status,fit_score,lease_until FROM companies").fetchall()
    part = {"complete": 0, "in_flight": 0, "parked": 0, "pending": 0}
    for f, t, c, fit, lease in rows:
        if "failed" in (f, t, c):                       part["parked"] += 1
        elif fit is not None:                           part["complete"] += 1
        elif lease is not None and lease > NOW:         part["in_flight"] += 1
        else:                                           part["pending"] += 1
    return {"step": step, "label": label, **part}

def build_with_trace():
    db = os.path.join(HERE, "driver.db")
    if os.path.exists(db): os.remove(db)
    con = sqlite3.connect(db)
    con.executescript(open(os.path.join(HERE, "schema.driver.sql")).read())
    # identical initial state to harness.build_driver (seed rows + mid-pipeline leases)
    for i, dom in enumerate(WORLD, start=1):
        con.execute("INSERT INTO companies(id,domain,domain_fp,added_at,added_by) VALUES(?,?,?,?,?)",
                    (i, dom, dom.split('.')[0], NOW, "seed-bot"))
    for dom, claim in MID.items():
        w = WORLD[dom]["f"]
        con.execute("""UPDATE companies SET firmographics_status='done',industry=?,employee_count=?,hq_country=?,
                       claimed_by=?,claimed_at=?,lease_until=? WHERE domain=?""",
                    (w[1], w[2], w[3], claim["claimed_by"], NOW, claim["lease_until"], dom))
    con.commit()

    frames = [snapshot(con, 0, "seeded")]
    step = 0
    for _pass in range(50):
        worked = 0
        for st in STAGES:
            while True:
                row = claim_next(con, st)
                if row is None: break
                worked += 1; step += 1
                do_stage(con, st, row)            # snapshot AFTER release -> row is at rest, never mid-claim
                frames.append(snapshot(con, step, f"{st['name']}:{row[1]}"))
        if worked == 0: break
    con.commit(); con.close()
    return frames

if __name__ == "__main__":
    frames = build_with_trace()
    with open(OUT, "w") as fh:
        for fr in frames:
            fh.write(json.dumps(fr) + "\n")
    print(f"wrote {OUT}  ({len(frames)} frames)")
    print("  final: " + ", ".join(f"{k}={frames[-1][k]}" for k in ("complete", "in_flight", "parked", "pending")))
