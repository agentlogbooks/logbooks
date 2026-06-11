#!/usr/bin/env python3
"""
Build the company-enrichment driver logbook, accumulate data through all four
phases with atomic claim-and-advance, and build a naive (anti-pattern) contrast DB.

Deterministic: fixed clock, fixed per-domain outcomes ("the world"). No randomness.
Run:  python3 harness.py   ->  writes driver.db and naive.db, prints final states.

World encoding (trailing int = fail_count: leading attempts that error before success;
fail_count >= N_ATTEMPTS means POISON, i.e. it never succeeds and gets parked):
  f: ("done", industry, employees, country, fail_count)
  t: ("done", cms, analytics, cloud, fail_count) | ("none", fail_count)
  c: ("done", email, name, fail_count)            | ("nocontact", fail_count)
  s: int
"""
import os, sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
NOW   = "2026-06-11T12:00:00Z"           # fixed clock for the whole run
LEASE = "2026-06-11T12:15:00Z"           # now + 15m, written when a worker claims
N_ATTEMPTS = 3                           # poison cap (Decision 4)

WORLD = {
  "acme.com":      dict(f=("done","SaaS",420,"US",0),        t=("done","WordPress","GA4","AWS",0),  c=("done","cto@acme.com","Lee",0),     s=88),
  "globex.com":    dict(f=("done","Manufacturing",9000,"DE",0), t=("done","AEM","Adobe","Azure",0), c=("done","ir@globex.com","Mara",0),   s=74),
  "initech.com":   dict(f=("done","Finance",230,"US",0),     t=("done","Drupal","GA4","GCP",0),     c=("done","ops@initech.com","Bill",0), s=63),
  "umbrella.com":  dict(f=("done","Pharma",51000,"GB",0),    t=("none",0),                          c=("done","press@umbrella.com","V",0), s=70),  # legit-empty techstack
  "soylent.com":   dict(f=("done","Food",1200,"US",0),       t=("done","Shopify","Segment","AWS",0),c=("nocontact",0),                     s=58),  # legit-empty contacts
  "wonka.com":     dict(f=("done","Confectionery",500,"US",99), t=("done","x","x","x",0),           c=("done","a@b.com","c",0),            s=1),   # POISON firmographics
  "stark.com":     dict(f=("done","Defense",30000,"US",0),   t=("done","Custom","Snowplow","AWS",0),c=("done","jarvis@stark.com","P",0),   s=95),
  "wayne.com":     dict(f=("done","Holding",70000,"US",0),   t=("done","WordPress","GA4","Azure",0),c=("done","alfred@wayne.com","B",0),   s=81),  # in-flight (active lease)
  "cyberdyne.com": dict(f=("done","Robotics",1500,"US",0),   t=("done","x","x","x",99),             c=("done","skynet@cyberdyne.com","M",0),s=44), # POISON techstack -> parked
  "tyrell.com":    dict(f=("done","Biotech",6000,"US",0),    t=("done","Custom","GA4","GCP",0),     c=("done","roy@tyrell.com","E",0),     s=67),
  "oscorp.com":    dict(f=("done","Chemicals",800,"US",1),   t=("done","WordPress","GA4","AWS",0),  c=("done","norman@oscorp.com","H",0),  s=72),  # transient firmographics then ok
  "dunder.com":    dict(f=("done","Paper",60,"US",0),        t=("done","Wix","GA4","Heroku",0),     c=("done","michael@dunder.com","D",0), s=49),  # stale claim -> reclaimed
}

# rows seeded mid-pipeline (firmographics already done before the loop runs)
MID = {
  "wayne.com":  dict(claimed_by="worker-7",    lease_until="2026-06-11T12:30:00Z"),  # FUTURE lease -> in-flight, loop skips
  "dunder.com": dict(claimed_by="worker-dead", lease_until="2026-06-11T11:00:00Z"),  # PAST lease  -> reclaimable
}

_attempt_log = {}
def _attempts_so_far(dom, stage): return _attempt_log.get((dom, stage), 0)
def _bump(dom, stage): _attempt_log[(dom, stage)] = _attempts_so_far(dom, stage) + 1

STAGES = [
  dict(name="firmographics", status="firmographics_status", att="firmographics_attempts",
       ready="firmographics_status IS NULL"),
  dict(name="techstack", status="techstack_status", att="techstack_attempts",
       ready="techstack_status IS NULL AND firmographics_status='done'"),
  dict(name="contacts", status="contacts_status", att="contacts_attempts",
       ready="contacts_status IS NULL AND techstack_status IN ('done','none-detected')"),
  dict(name="score", status="fit_score", att=None,
       ready="fit_score IS NULL AND contacts_status IN ('done','no-contact')"),
]
KEY = {"firmographics":"f","techstack":"t","contacts":"c","score":"s"}

def build_driver():
    db = os.path.join(HERE, "driver.db")
    if os.path.exists(db): os.remove(db)
    con = sqlite3.connect(db)
    con.executescript(open(os.path.join(HERE, "schema.driver.sql")).read())
    for i, dom in enumerate(WORLD, start=1):
        con.execute("INSERT INTO companies(id,domain,domain_fp,added_at,added_by) VALUES(?,?,?,?,?)",
                    (i, dom, dom.split('.')[0], NOW, "seed-bot"))
    for dom, claim in MID.items():
        w = WORLD[dom]["f"]
        con.execute("""UPDATE companies SET firmographics_status='done',
                       industry=?, employee_count=?, hq_country=?,
                       claimed_by=?, claimed_at=?, lease_until=? WHERE domain=?""",
                    (w[1], w[2], w[3], claim["claimed_by"], NOW, claim["lease_until"], dom))
    con.commit()

    for _pass in range(50):
        worked = 0
        for st in STAGES:
            while True:
                row = claim_next(con, st)
                if row is None: break
                worked += 1
                do_stage(con, st, row)
        if worked == 0: break
    con.commit(); con.close()
    return db

def claim_next(con, st):
    att_clause = f" AND {st['att']} < {N_ATTEMPTS}" if st['att'] else ""
    sql = f"""
      UPDATE companies SET claimed_by='loop', claimed_at=?, lease_until=?
       WHERE id = (SELECT id FROM companies
                    WHERE {st['ready']}{att_clause}
                      AND (lease_until IS NULL OR lease_until < ?)
                    ORDER BY added_at, id LIMIT 1)
      RETURNING id, domain"""
    return con.execute(sql, (NOW, LEASE, NOW)).fetchone()

def do_stage(con, st, row):
    rid, dom = row
    name = st["name"]

    def release(extra="", params=()):
        con.execute(f"UPDATE companies SET claimed_by=NULL, claimed_at=NULL, lease_until=NULL{extra} WHERE id=?",
                    (*params, rid))
        con.commit()

    if name == "score":
        con.execute("UPDATE companies SET fit_score=?, scored_at=? WHERE id=?", (WORLD[dom]["s"], NOW, rid))
        release(); return

    out = WORLD[dom][KEY[name]]
    kind, fail_count = out[0], out[-1]
    prior = _attempts_so_far(dom, name)
    if prior < fail_count:                       # this attempt errors
        _bump(dom, name); new_att = prior + 1
        if new_att >= N_ATTEMPTS:
            release(f", {st['status']}='failed', {st['att']}=?", (new_att,))   # parked (poison)
        else:
            release(f", {st['att']}=?", (new_att,))                            # transient -> retry
        return
    # success
    if name == "firmographics":
        release(f", {st['status']}='done', industry=?, employee_count=?, hq_country=?", (out[1], out[2], out[3]))
    elif name == "techstack":
        if kind == "none": release(f", {st['status']}='none-detected'")
        else:              release(f", {st['status']}='done', cms=?, analytics=?, cloud=?", (out[1], out[2], out[3]))
    elif name == "contacts":
        if kind == "nocontact": release(f", {st['status']}='no-contact'")
        else:                   release(f", {st['status']}='done', primary_email=?, contact_name=?", (out[1], out[2]))

# ---- naive contrast DB -------------------------------------------------------
def _writable(dom, key):
    """What a naive worker can write this pass: None if it errors (poison) or has no content (legit-empty)."""
    w = WORLD[dom][key]
    if w[-1] >= N_ATTEMPTS: return None      # poison: errors every pass, writes nothing
    if w[0] == "done":      return w         # has content
    return None                              # 'none'/'nocontact': legitimately empty, nothing to write

def build_naive():
    db = os.path.join(HERE, "naive.db")
    if os.path.exists(db): os.remove(db)
    con = sqlite3.connect(db)
    con.executescript(open(os.path.join(HERE, "schema.naive.sql")).read())
    for i, dom in enumerate(WORLD, start=1):
        con.execute("INSERT INTO companies_naive(id,domain,added_at) VALUES(?,?,?)", (i, dom, NOW))
    con.commit()

    pending_sql = {
      "firmographics": "industry IS NULL",
      "techstack":     "cms IS NULL AND analytics IS NULL AND cloud IS NULL",
      "contacts":      "primary_email IS NULL",
      "score":         "fit_score IS NULL",
    }
    history = []
    for _pass in range(6):
        for dom in WORLD:
            ind, cms, ana, cl, email, score = con.execute(
                "SELECT industry,cms,analytics,cloud,primary_email,fit_score FROM companies_naive WHERE domain=?", (dom,)).fetchone()
            if ind is None:                                   # phase 1 (content-pending)
                w = _writable(dom, "f")
                if w: con.execute("UPDATE companies_naive SET industry=?,employee_count=?,hq_country=? WHERE domain=?", (w[1],w[2],w[3],dom))
            elif cms is None and ana is None and cl is None:  # phase 2
                w = _writable(dom, "t")
                if w: con.execute("UPDATE companies_naive SET cms=?,analytics=?,cloud=? WHERE domain=?", (w[1],w[2],w[3],dom))
            elif email is None:                               # phase 3
                w = _writable(dom, "c")
                if w: con.execute("UPDATE companies_naive SET primary_email=?,contact_name=? WHERE domain=?", (w[1],w[2],dom))
            elif score is None:                               # phase 4
                con.execute("UPDATE companies_naive SET fit_score=? WHERE domain=?", (WORLD[dom]["s"], dom))
        con.commit()
        history.append({ph: con.execute(f"SELECT count(*) FROM companies_naive WHERE {q}").fetchone()[0] for ph,q in pending_sql.items()})
    con.close()
    return db, history

def report_driver(db):
    con = sqlite3.connect(db)
    print("\n=== DRIVER logbook final state (driver.db) ===")
    rows = con.execute("""SELECT domain, firmographics_status, techstack_status, contacts_status,
                          fit_score, lease_until FROM companies ORDER BY id""").fetchall()
    print(f"{'domain':<16}{'firm':<8}{'tech':<14}{'contact':<12}{'score':<7}{'lease':<22}")
    for d,f,t,c,s,lu in rows:
        print(f"{d:<16}{str(f):<8}{str(t):<14}{str(c):<12}{str(s):<7}{(lu if lu else '-'):<22}")
    con.close()

def report_naive(db, history):
    print("\n=== NAIVE contrast (naive.db) -- rows still 'pending' (content NULL) per pass ===")
    print(f"{'pass':<6}{'firmographics':<16}{'techstack':<12}{'contacts':<11}{'score':<7}")
    for i,h in enumerate(history,1):
        print(f"{i:<6}{h['firmographics']:<16}{h['techstack']:<12}{h['contacts']:<11}{h['score']:<7}")
    print("  -> never converges to 0: umbrella (none-detected tech), soylent (no-contact),")
    print("     wonka & cyberdyne (poison) leave content NULL while being legitimately done/parked,")
    print("     so the naive queue cannot tell 'complete' from 'pending'. Completeness is unprovable.")

if __name__ == "__main__":
    d = build_driver()
    n, hist = build_naive()
    report_driver(d)
    report_naive(n, hist)
    print(f"\nWrote {d}\nWrote {n}")
