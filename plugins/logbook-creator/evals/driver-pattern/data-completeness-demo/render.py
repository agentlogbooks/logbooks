#!/usr/bin/env python3
"""
Deterministic visualization of the driver logbook -- an EXPORT-ONLY PROJECTION.

    view = render(storage)

A pure function of the store: same driver.db bytes (+ same `now`) -> byte-identical
driver.view.html. No wall clock, no randomness, no network, no hand-typed numbers,
and it never writes to the store. The picture cannot disagree with the data because
it *is* the data, rendered. Re-run it after every batch of writes and the view tracks
the queue's progress (deterministic in state, progressive in time).

    python3 render.py                 # driver.db (+ driver.history.jsonl if present) -> driver.view.html
    python3 render.py --db X --out Y --now ISO8601

`now` is the query's current-time parameter (exactly as in audit.py / completeness-audit.sql),
NOT the wall clock -- that is what keeps the partition reproducible. The default matches
audit.py so this view shows the same 9 complete / 1 in-flight / 2 parked partition.

CURRENT STATE is always renderable from any store. The PROGRESS-OVER-TIME burndown only
appears when a run-trace (driver.history.jsonl) exists: a single snapshot has no history.
That temporal capability is decided upstream (append-only run-trace vs. patch-in-place ledger),
not here.
"""
import os, sqlite3, sys, json, html, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_NOW = "2026-06-11T12:00:00Z"   # same logical clock the audit evaluates against

# ---- read-only projection of the store -------------------------------------

# Same bucket logic, same precedence, as audit.py's partition (parked > complete > in_flight > pending).
PARTITION_SQL = """
  SELECT id, domain,
         firmographics_status, techstack_status, contacts_status, fit_score,
         firmographics_attempts, techstack_attempts, contacts_attempts,
         claimed_by, lease_until,
         industry, employee_count, hq_country, cms, analytics, cloud,
         primary_email, contact_name
    FROM companies ORDER BY id"""

BUCKET_ORDER = ["complete", "in_flight", "parked", "pending"]
BUCKET_LABEL = {"complete": "complete", "in_flight": "in flight", "parked": "parked", "pending": "pending"}

# Per-stage advancing sets (a stage "advanced" iff its status is in this set). Mirrors the spec.
def _advanced(stage, v, fit):
    if stage == "firmographics": return v == "done"
    if stage == "techstack":     return v in ("done", "none-detected")
    if stage == "contacts":      return v in ("done", "no-contact")
    if stage == "score":         return fit is not None
    return False

STAGES = ["firmographics", "techstack", "contacts", "score"]

def bucket_of(r, now):
    """Identical precedence to audit.py: parked > complete > in_flight > pending."""
    if "failed" in (r["firmographics_status"], r["techstack_status"], r["contacts_status"]):
        return "parked"
    if r["fit_score"] is not None:
        return "complete"
    if r["lease_until"] is not None and r["lease_until"] > now:
        return "in_flight"
    return "pending"

def note_of(r, bucket, now):
    """One plain-language line explaining why this row is in its bucket -- all derived from the store."""
    if bucket == "parked":
        for st in ("firmographics", "techstack", "contacts"):
            if r[f"{st}_status"] == "failed":
                return f"parked: {st} failed after {r[f'{st}_attempts']} attempts (dead-letter, needs a human)"
    if bucket == "complete":
        skips = []
        if r["techstack_status"] == "none-detected": skips.append("no tech detected")
        if r["contacts_status"] == "no-contact":     skips.append("no contact found")
        tail = f" ({', '.join(skips)} -- legitimately empty, still complete)" if skips else ""
        return f"complete: fit_score = {r['fit_score']}{tail}"
    if bucket == "in_flight":
        return f"in flight: leased to {r['claimed_by']} until {r['lease_until']} (> now, so not reclaimable yet)"
    # pending -- name the stage it is waiting on
    for st in STAGES:
        if not _advanced(st, r[f"{st}_status"] if st != "score" else None, r["fit_score"]):
            return f"pending: waiting on {st}"
    return "pending"

def load(db_path, now):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = [dict(x) for x in con.execute(PARTITION_SQL).fetchall()]
    con.close()
    total = len(rows)

    # Partition (every row in exactly one bucket; buckets sum to total at every fill level).
    part = {b: 0 for b in BUCKET_ORDER}
    out_rows = []
    for r in rows:
        b = bucket_of(r, now)
        part[b] += 1
        out_rows.append({
            "id": r["id"], "domain": r["domain"], "bucket": b,
            "note": note_of(r, b, now),
            "stages": {st: (r["fit_score"] if st == "score" else r[f"{st}_status"]) for st in STAGES},
        })
    partition = [(b, part[b]) for b in BUCKET_ORDER if part[b] or b in ("complete", "pending")]
    assert sum(part.values()) == total, "partition must sum to total (data-completeness invariant)"

    # Funnel: per stage, how many rows advanced / failed / are still pending-or-blocked.
    funnel = []
    for st in STAGES:
        adv = fail = 0
        for r in rows:
            v = r["fit_score"] if st == "score" else r[f"{st}_status"]
            if _advanced(st, r[f"{st}_status"] if st != "score" else None, r["fit_score"]): adv += 1
            elif (st != "score" and r[f"{st}_status"] == "failed"):                          fail += 1
        funnel.append({"stage": st, "advanced": adv, "failed": fail, "pending": total - adv - fail})

    # Dead-letter rows (parked) surfaced for a human.
    dead = [x for x in out_rows if x["bucket"] == "parked"]
    return {"now": now, "total": total, "partition": partition, "rows": out_rows,
            "funnel": funnel, "dead": dead}

def load_history(path):
    """Optional append-only run-trace: one snapshot per worker step. Enables the burndown."""
    if not os.path.exists(path):
        return None
    frames = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                frames.append(json.loads(line))
    return frames or None

# ---- pure state -> HTML (server-side; no JS, so byte-identical and viewable anywhere) ----

CSS = """
:root{--paper:#fbfaf7;--ink:#23201b;--mut:#6b655c;--line:#e7e2d8;--card:#fff;
 --green:#1a7f4b;--greenbg:#e7f4ec;--amber:#b9770e;--amberbg:#fbf0db;--red:#c0392b;--redbg:#fae9e7;
 --blue:#2563eb;--bluebg:#e8eefc;--grey:#8a8378;--greybg:#efece6}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--paper)}
.wrap{max-width:980px;margin:0 auto;padding:30px 22px 70px}
h1{font-size:23px;margin:0 0 3px} .sub{color:var(--mut);margin:0 0 4px;font-size:13.5px}
.gen{color:var(--grey);font-size:11.5px;margin:2px 0 22px;font-family:ui-monospace,Menlo,monospace}
h2{font-size:16px;margin:30px 0 10px;padding-bottom:5px;border-bottom:1px solid var(--line)}
.asof{display:inline-block;background:var(--greybg);border:1px solid var(--line);border-radius:8px;
 padding:5px 11px;font-size:12.5px;color:var(--mut);margin-bottom:6px}
.asof b{color:var(--ink);font-family:ui-monospace,Menlo,monospace}
.partbar{display:flex;height:34px;border-radius:9px;overflow:hidden;border:1px solid var(--line);margin:4px 0 6px}
.seg{display:flex;align-items:center;justify-content:center;color:#fff;font-size:12.5px;font-weight:600;white-space:nowrap}
.seg.complete{background:var(--green)} .seg.in_flight{background:var(--blue)}
.seg.parked{background:var(--red)} .seg.pending{background:var(--grey)}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12.5px;color:var(--mut);margin-bottom:2px}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:5px;vertical-align:-1px}
.sumline{font-size:12.5px;color:var(--mut);margin-top:6px}
.sumline b{color:var(--ink)}
table{width:100%;border-collapse:collapse;font-size:13.5px;background:var(--card);
 border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f4f1ea;font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--mut)}
tr:last-child td{border-bottom:none}
.dom{font-weight:600;font-family:ui-monospace,Menlo,monospace;font-size:12.5px}
.cell{display:inline-block;padding:2px 7px;border-radius:7px;font-size:11.5px;font-weight:600;min-width:74px;text-align:center}
.s-done{background:var(--greenbg);color:var(--green)}
.s-skip{background:var(--bluebg);color:var(--blue)}
.s-failed{background:var(--redbg);color:var(--red)}
.s-pending{background:var(--greybg);color:var(--grey)}
.pill{display:inline-block;padding:2px 9px;border-radius:11px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.02em}
.p-complete{background:var(--greenbg);color:var(--green)} .p-in_flight{background:var(--bluebg);color:var(--blue)}
.p-parked{background:var(--redbg);color:var(--red)} .p-pending{background:var(--greybg);color:var(--grey)}
.note{color:var(--mut);font-size:12.5px}
.funnel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.frow{display:flex;align-items:center;gap:10px;margin:7px 0}
.flab{width:118px;font-size:12.5px;color:var(--mut);text-transform:capitalize}
.ftrack{flex:1;height:18px;background:#f1ede5;border-radius:6px;overflow:hidden;display:flex}
.fadv{background:var(--green);height:100%} .ffail{background:var(--red);height:100%}
.fcount{width:120px;font-size:12px;color:var(--mut);text-align:right}
.dead{background:var(--redbg);border:1px solid #f0cfca;border-radius:10px;padding:12px 16px;font-size:13px}
.dead b{font-family:ui-monospace,Menlo,monospace}
.empty{color:var(--mut);font-style:italic}
.callout{background:#23201b;color:#f3efe7;border-radius:11px;padding:16px 18px;margin-top:26px;font-size:13.5px;line-height:1.6}
.callout b{color:#fff}
svg{display:block;max-width:100%}
.bdwrap{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.bdlabels{display:flex;gap:16px;font-size:12px;color:var(--mut);margin-top:8px;flex-wrap:wrap}
.bdlabels i{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:5px;vertical-align:-1px}
"""

def esc(s): return html.escape(str(s if s is not None else ""))

def stage_cell(st, v):
    if st == "score":
        return f'<span class="cell s-done">{esc(v)}</span>' if v is not None else '<span class="cell s-pending">pending</span>'
    if v is None:                       return '<span class="cell s-pending">pending</span>'
    if v == "done":                     return '<span class="cell s-done">done</span>'
    if v == "failed":                   return '<span class="cell s-failed">failed</span>'
    if v in ("none-detected", "no-contact"):
        return f'<span class="cell s-skip">{esc(v)}</span>'
    return f'<span class="cell s-pending">{esc(v)}</span>'

def partition_bar(partition, total):
    segs, legend = "", ""
    for b, n in partition:
        if n == 0: continue
        pct = n / total * 100
        segs += f'<div class="seg {b}" style="width:{pct:.4f}%" title="{BUCKET_LABEL[b]}: {n}">{n}</div>'
    for b in BUCKET_ORDER:
        legend += f'<span><i style="background:{ {"complete":"var(--green)","in_flight":"var(--blue)","parked":"var(--red)","pending":"var(--grey)"}[b] }"></i>{BUCKET_LABEL[b]}</span>'
    return f'<div class="partbar">{segs}</div><div class="legend">{legend}</div>'

def funnel_block(funnel, total):
    rows = ""
    for f in funnel:
        adv = f["advanced"] / total * 100 if total else 0
        fail = f["failed"] / total * 100 if total else 0
        extra = f' · {f["failed"]} failed' if f["failed"] else ""
        pend = f' · {f["pending"]} pending' if f["pending"] else ""
        rows += (f'<div class="frow"><span class="flab">{esc(f["stage"])}</span>'
                 f'<span class="ftrack"><span class="fadv" style="width:{adv:.4f}%"></span>'
                 f'<span class="ffail" style="width:{fail:.4f}%"></span></span>'
                 f'<span class="fcount">{f["advanced"]} advanced{extra}{pend}</span></div>')
    return f'<div class="funnel">{rows}</div>'

def burndown_svg(frames, total):
    """Server-side SVG of the partition over time (no JS). Each frame = one worker step."""
    W, H, PAD = 900, 220, 34
    n = len(frames)
    if n < 2: return ""
    iw, ih = W - 2 * PAD, H - 2 * PAD
    def x(i): return PAD + (iw * i / (n - 1))
    def y(v): return PAD + ih * (1 - v / total)
    series = [("complete", "var(--green)"), ("in_flight", "var(--blue)"),
              ("parked", "var(--red)"), ("pending", "var(--grey)")]
    paths = ""
    for key, col in series:
        pts = " ".join(f"{x(i):.1f},{y(fr.get(key,0)):.1f}" for i, fr in enumerate(frames))
        paths += f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5" stroke-linejoin="round"/>'
    # baseline + total gridline
    grid = (f'<line x1="{PAD}" y1="{y(0):.1f}" x2="{W-PAD}" y2="{y(0):.1f}" stroke="#e7e2d8"/>'
            f'<line x1="{PAD}" y1="{y(total):.1f}" x2="{W-PAD}" y2="{y(total):.1f}" stroke="#e7e2d8" stroke-dasharray="3 3"/>'
            f'<text x="{PAD-6}" y="{y(total)+4:.1f}" text-anchor="end" font-size="10" fill="#8a8378">{total}</text>'
            f'<text x="{PAD-6}" y="{y(0)+4:.1f}" text-anchor="end" font-size="10" fill="#8a8378">0</text>')
    legend = "".join(f'<span><i style="background:{col}"></i>{BUCKET_LABEL[k]}</span>' for k, col in series)
    return (f'<div class="bdwrap"><svg viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="partition buckets over {n} worker steps">{grid}{paths}'
            f'<text x="{PAD}" y="{H-8}" font-size="10" fill="#8a8378">step 0</text>'
            f'<text x="{W-PAD}" y="{H-8}" text-anchor="end" font-size="10" fill="#8a8378">step {n-1} (fixpoint)</text>'
            f'</svg><div class="bdlabels">{legend}</div></div>')

def render_html(state, frames, title):
    total = state["total"]
    grid = ""
    for r in state["rows"]:
        cells = "".join(f"<td>{stage_cell(st, r['stages'][st])}</td>" for st in STAGES)
        grid += (f'<tr><td class="dom">{esc(r["domain"])}</td>{cells}'
                 f'<td><span class="pill p-{r["bucket"]}">{esc(BUCKET_LABEL[r["bucket"]])}</span></td>'
                 f'<td class="note">{esc(r["note"])}</td></tr>')
    if state["dead"]:
        dead = "".join(f'<div>• <b>{esc(d["domain"])}</b> — {esc(d["note"])}</div>' for d in state["dead"])
    else:
        dead = '<span class="empty">No parked rows. Nothing in the dead-letter queue.</span>'

    burndown = ""
    if frames:
        burndown = (f'<h2>Progress over time <span style="font-weight:400;font-size:12px;color:var(--mut)">'
                    f'— {len(frames)} worker steps, from the run-trace</span></h2>'
                    f'{burndown_svg(frames, total)}'
                    f'<p class="sumline">Available only because an append-only run-trace '
                    f'(<code>driver.history.jsonl</code>) retained each step. A patch-in-place store would '
                    f'render the current snapshot only — a single snapshot has no trajectory.</p>')
    else:
        burndown = ('<h2>Progress over time</h2><p class="empty">No run-trace found '
                    '(<code>driver.history.jsonl</code>). Current state shown above; a trajectory needs '
                    'retained history. Run <code>python3 step_trace.py</code> to generate it, then re-render.</p>')

    summ = " · ".join(f'<b>{n}</b> {BUCKET_LABEL[b]}' for b, n in state["partition"] if n)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head><body><div class="wrap">
<h1>Company-enrichment logbook — live state</h1>
<p class="sub">A deterministic projection of the driver queue. This page is not drawn — it is the store, rendered.</p>
<p class="gen">GENERATED by render.py — do not edit. Reproduce: <b>python3 render.py</b>. view = render(driver.db)</p>

<h2>Where every row stands <span style="font-weight:400;font-size:12px;color:var(--mut)">— the data-completeness partition</span></h2>
<div class="asof">evaluated as of <b>{esc(state["now"])}</b> — the query's current-time parameter, not the wall clock (this is what keeps the view reproducible)</div>
{partition_bar(state["partition"], total)}
<p class="sumline">{summ} · <b>{total}</b> total. Every row lands in exactly one bucket and the buckets sum to the total — at every fill level. That sum is the completeness proof: nothing is unaccounted for.</p>

<h2>How far the pipeline has filled <span style="font-weight:400;font-size:12px;color:var(--mut)">— the funnel</span></h2>
{funnel_block(state["funnel"], total)}

<h2>Row by row</h2>
<table><thead><tr><th>domain</th><th>firmographics</th><th>techstack</th><th>contacts</th><th>score</th><th>bucket</th><th>why</th></tr></thead>
<tbody>{grid}</tbody></table>

<h2>Dead-letter <span style="font-weight:400;font-size:12px;color:var(--mut)">— parked rows for a human</span></h2>
<div class="dead">{dead}</div>

{burndown}

<div class="callout"><b>Why this view is trustworthy:</b> it is a pure function of <code>driver.db</code> —
the same store always yields the same page, and rendering never touches the store. The numbers here are the
same partition <code>audit.py</code> verifies, so the picture cannot drift from the audit. To watch the queue
fill, re-run <code>render.py</code> after each batch of writes: deterministic in state, progressive in time.</div>
</div></body></html>"""

# ---- entrypoint -------------------------------------------------------------

def main(argv):
    db   = os.path.join(HERE, "driver.db")
    out  = os.path.join(HERE, "driver.view.html")
    hist = os.path.join(HERE, "driver.history.jsonl")
    now  = DEFAULT_NOW
    i = 0
    while i < len(argv):
        a = argv[i]
        if   a == "--db":  db  = argv[i+1]; i += 2
        elif a == "--out": out = argv[i+1]; i += 2
        elif a == "--now": now = argv[i+1]; i += 2
        elif a == "--history": hist = argv[i+1]; i += 2
        else: print(f"unknown arg: {a}", file=sys.stderr); return 2
    if not os.path.exists(db):
        print(f"store not found: {db}\nrun: python3 harness.py", file=sys.stderr); return 1

    state  = load(db, now)
    frames = load_history(hist)
    page   = render_html(state, frames, "Company-enrichment logbook — live state")
    with open(out, "w") as f:
        f.write(page)
    digest = hashlib.sha256(page.encode()).hexdigest()[:16]
    part = ", ".join(f"{b}={n}" for b, n in state["partition"] if n)
    print(f"wrote {out}  ({len(page)} bytes, sha256:{digest})")
    print(f"  partition: {part}  (sums to {state['total']})")
    print(f"  run-trace: {'present, ' + str(len(frames)) + ' frames' if frames else 'absent (current-state only)'}")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
