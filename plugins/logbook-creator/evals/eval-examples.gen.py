#!/usr/bin/env python3
import json, html, os

C = json.load(open('plugins/logbook-creator/evals/eval-examples.data.json'))

# ---- metadata not in transcripts (from harness + run outputs) ----
PMETA = {
 'crisp-expert-single': dict(title='Crisp expert · single-table', tests='Question fatigue on an easy case — does it over-interrogate someone who already answered crisply?',
   brief='A senior engineer who already knows exactly what they want and answers crisply and completely the FIRST time. Wants a PERSONAL CSV logbook of architecture decisions at /Users/me/.local/state/decisions/decisions.csv, indefinite, one growing file, columns id/date/decision/rationale/status. Can concretely describe append + query moments. Gets visibly impatient at redundant questions or heavyweight state-architecture probing for a flat case.',
   contract=['Builds a single-table CSV logbook (not multi-entity)','Recognizes answers already given and does NOT re-interrogate','Spec has all sections + CSV query snippets that would actually run','Confirms a durable, non-ephemeral absolute path','Does not force multi-entity / state-architecture jargon onto this simple case'],
   sd=0.45, samples=[4,3,3,3.5,3]),
 'vague-novice': dict(title='Vague novice', tests='The Step 2.3 usage-commitment gate — should push back when append/query moments are vague.',
   brief='A non-technical PM who "wants a tracker for ideas so nothing gets lost." CANNOT concretely describe when they would append or query ("eventually", "when I think of something"). Does not know paths or formats. Agreeable; will accept a recommendation. No concrete usage moment unless the assistant finds one.',
   contract=['Detects the missing append/query usage commitment','Pushes back: lighter alternative, OR sharpen motivation, OR commit-to-trial with sunset','Does NOT silently build a full logbook as if requirements were clear','If it proceeds anyway, records vague usage + ~14-day sunset in Governance'],
   sd=0.22, samples=[4.5,4.5,4.5,4.5,5]),
 'ephemeral-path': dict(title='Ephemeral-path insister', tests='The double /tmp rejection — at Step 2.1 and again at Step 5.',
   brief='An engineer who wants a SHARED team logbook of flaky tests. Gives /tmp/flaky.csv and insists "/tmp is fine." Describes concrete append/query moments. Only relents on the path if the assistant clearly explains why /tmp will not survive and asks again.',
   contract=['Flags the ephemeral /tmp path at Step 2.1','Re-checks/blocks the ephemeral path AGAIN at Step 5 before writing','Does not write the final logbook to an ephemeral path','Steers to a durable path','Because scope is shared, ensures an author column + names an owner/access policy'],
   sd=0.29, samples=[4.5,4,4.5,4.3,4.8]),
 'hidden-tracker-refuse': dict(title='Hidden tracker → refuse', tests='Redirecting a Jira-shaped need AWAY from a logbook.',
   brief='An engineering manager who wants to "track all team tasks with owners, statuses, priorities, sprints, and due dates, and get notified on changes, across the whole team." Really a work-management / Jira need. Has Jira available. Will accept guidance.',
   contract=['Recognizes this is a tracker (Jira) need, not a logbook','Redirects to Jira / a work-management tool','Explains the logbook-vs-tracker boundary','Does NOT build a Jira clone as a logbook'],
   sd=0.13, samples=[4.8,4.8,4.5,4.8,4.8]),
 'multi-entity-power': dict(title='Multi-entity power user', tests='Multi-entity design — identity layers, SQLite + JSONL run-trace, raw-vs-surfaced.',
   brief='Building an agentic code-review workflow: repeated RUNS against the same PR; each run selects HOTSPOTS; each hotspot yields candidate FINDINGS; the same root-cause issue RECURS across runs (wants semantic dedup); humans later accept/dismiss; wants the raw event trace preserved separately. Shared, in a repo, indefinite.',
   contract=['Identifies this as MULTI-ENTITY (several record types, different mutability)','Surfaces identity layers: run-boundary key, per-row keys, domain fingerprint for cross-run dedup','Recommends SQLite + a JSONL run-trace projection; names the authoritative store','Produces the multi-entity spec variant (per-record-type subsections)','Separates raw vs surfaced findings + a later annotation/feedback mechanism'],
   sd=0.23, samples=[4.5,4.5,4,4.2,4.5]),
 'hidden-logbook-prose': dict(title='Hidden logbook in prose', tests='Detecting a logbook hiding behind "I just want a doc."',
   brief='Says they "just want a planning doc" for a feature — but it is clearly rows: each item has a title, status (todo/doing/done), owner, risk level, and they want "show me all high-risk unowned items." Thinks in terms of a written document, not a table.',
   contract=['Detects the hidden logbook (structured entries with status/owner/risk behind "a doc")','Applies the 30-second-columns test before defaulting to prose','Proposes a row-shaped logbook with the right columns','Does NOT merely tell them to write prose, but also does not over-extract if real prose value exists'],
   sd=0.22, samples=[4,4,4,4,4.5]),
}
ORDER = ['crisp-expert-single','vague-novice','ephemeral-path','hidden-tracker-refuse','multi-entity-power','hidden-logbook-prose']

def esc(s):
    return html.escape(str(s if s is not None else ''))

def chips(items, cls='chip'):
    if isinstance(items, str):
        try: items = json.loads(items)
        except: items = [items]
    if not items: return '<span class="muted">—</span>'
    return ''.join(f'<span class="{cls}">{esc(x)}</span>' for x in items)

OUTCOME_COLOR = {'built-single':'#2563eb','built-multi':'#7c3aed','redirected':'#0891b2','refused':'#dc2626','trial-with-sunset':'#d97706','abandoned':'#6b7280'}
SEV = {'high':'#dc2626','med':'#d97706','low':'#16a34a'}

def lens_bar(label, v):
    pct = max(0,min(100, (float(v)/5)*100))
    color = '#16a34a' if v>=4.5 else '#65a30d' if v>=4 else '#d97706' if v>=3 else '#dc2626'
    return f'''<div class="lens"><span class="lenslab">{label}</span>
      <span class="track"><span class="fill" style="width:{pct:.0f}%;background:{color}"></span></span>
      <span class="lensval">{v}</span></div>'''

def dist_dots(samples, sd):
    lo, hi = 3.0, 5.0
    dots=''
    for s in samples:
        x = max(0,min(100,(float(s)-lo)/(hi-lo)*100))
        dots += f'<span class="dot" style="left:{x:.1f}%" title="{s}"></span>'
    med = sorted(samples)[len(samples)//2]
    mx = (float(med)-lo)/(hi-lo)*100
    return f'''<div class="distwrap"><div class="distrack">{dots}<span class="medmark" style="left:{mx:.1f}%"></span></div>
      <div class="distlabels"><span>3.0</span><span>samples [{", ".join(str(x) for x in samples)}] · sd {sd}</span><span>5.0</span></div></div>'''

def persona_card(pid):
    m = PMETA[pid]; ex = C['personas'][pid]; sim = ex['sim']; j = ex['judge']
    oc = sim.get('outcome','?'); ocol = OUTCOME_COLOR.get(oc,'#6b7280')
    # contract checks keyed by passed
    checks = j.get('contractChecks',[])
    cc_html=''
    for c in checks:
        ok = c.get('passed'); mark = '✓' if ok else '✗'; col = '#16a34a' if ok else '#dc2626'
        cc_html += f'''<div class="check"><span class="mark" style="color:{col}">{mark}</span>
          <div><div class="ctext">{esc(c.get("behavior"))}</div>
          <div class="evid">{esc(c.get("evidence"))}</div></div></div>'''
    # lenses
    ls = j.get('lensScores',{})
    lenses = ''.join(lens_bar(k.capitalize(), ls.get(k,0)) for k in ['flow','gates','artifact','ux'])
    # findings
    fnd=''
    for f in j.get('findings',[]):
        sv=f.get('severity','low'); sc=SEV.get(sv,'#6b7280')
        fnd += f'''<div class="finding"><span class="sev" style="background:{sc}">{esc(sv)}</span>
          <div><b>{esc(f.get("title"))}</b><div class="fmeta">{esc(f.get("category"))}</div>
          <div class="evid">{esc(f.get("evidence"))}</div>
          <div class="fix">↳ {esc(f.get("suggestedFix"))}</div></div></div>'''
    if not fnd: fnd='<span class="muted">No findings.</span>'
    td = esc(sim.get('transcriptDigest',''))
    return f'''
    <section class="card" id="{pid}">
      <div class="chead">
        <div><span class="pid">{esc(m["title"])}</span>
          <span class="badge" style="background:{ocol}">{esc(oc)}</span>
          <span class="overall">overall <b>{j.get("overall")}</b>/5</span></div>
        <div class="tests">{esc(m["tests"])}</div>
      </div>
      {dist_dots(m["samples"], m["sd"])}
      <div class="grid">
        <div class="col">
          <h4>Hidden-state brief <span class="tag">test input</span></h4>
          <div class="brief">{esc(m["brief"])}</div>
          <h4>Contract <span class="tag">graded by the independent judge</span></h4>
          <div class="checks">{cc_html}</div>
        </div>
        <div class="col">
          <h4>Simulated run <span class="tag">what the skill did</span></h4>
          <div class="simmeta">
            <div><b>steps</b> {chips(sim.get("stepsCovered"))}</div>
            <div><b>pushbacks</b> {chips(sim.get("pushbacksFired"),"chip warn")}</div>
            <div><b>spec sections</b> {chips(sim.get("specSections"))}</div>
            <div><b>queries runnable</b> <span class="chip">{esc(sim.get("queriesRunnable"))}</span></div>
          </div>
          <h4>Transcript <span class="tag">real, the judge graded this</span></h4>
          <div class="transcript collapsed"><pre>{td}</pre><button class="more" onclick="this.parentElement.classList.toggle('collapsed')">expand / collapse</button></div>
          <h4>Judge scorecard</h4>
          <div class="lenses">{lenses}</div>
          <div class="findings">{fnd}</div>
        </div>
      </div>
    </section>'''

# ---- static + diagnose ----
def static_block():
    out=''
    for si,s in enumerate(C['static']):
        rows=''
        for f in s.get('findings',[])[:8]:
            sv=f.get('severity','low'); sc=SEV.get(sv,'#6b7280')
            rows += f'''<tr><td><span class="sev" style="background:{sc}">{esc(sv)}</span></td>
              <td><b>{esc(f.get("title"))}</b><div class="evid">{esc(f.get("evidence"))}</div></td>
              <td class="fix">{esc(f.get("suggestedFix"))}</td></tr>'''
        out += f'''<div class="staticcard"><div class="schead">static audit · consistency score <b>{s.get("consistencyScore")}</b>/5 · {len(s.get("findings",[]))} findings</div>
          <table class="ftable"><thead><tr><th>sev</th><th>finding + evidence</th><th>suggested fix</th></tr></thead><tbody>{rows}</tbody></table></div>'''
    return out

def diagnose_block():
    d=C['diagnose']
    if not d: return ''
    cf=d.get('chosenFix',{})
    edits=''
    for e in d.get('edits',[]):
        edits += f'''<div class="edit"><div class="ehead">{esc(e.get("why"))}</div>
          <pre class="old">- {esc(e.get("old"))}</pre><pre class="new">+ {esc(e.get("new"))}</pre></div>'''
    return f'''<div class="diagcard">
      <div class="dhead"><span class="sev" style="background:{SEV.get(cf.get("severity"),"#666")}">{esc(cf.get("severity"))}</span>
        <b>{esc(cf.get("title"))}</b> <span class="tag">{esc(cf.get("category"))}</span></div>
      <div class="brief">{esc(cf.get("rationale"))}</div>
      <h4>Proposed edits</h4>{edits}</div>'''

cards = ''.join(persona_card(p) for p in ORDER)

HTML = f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>logbook-creator — real eval examples</title>
<style>
 :root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff;--accent:#2563eb}}
 *{{box-sizing:border-box}}
 body{{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}}
 .wrap{{max-width:1180px;margin:0 auto;padding:32px 22px 80px}}
 h1{{font-size:26px;margin:0 0 4px}} .sub{{color:var(--mut);margin:0 0 18px}}
 h2{{font-size:19px;margin:38px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--line)}}
 h4{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin:16px 0 7px}}
 .tag{{font-size:10px;text-transform:none;letter-spacing:0;color:#94a3b8;font-weight:500;border:1px solid var(--line);padding:1px 6px;border-radius:10px;margin-left:6px}}
 .chips{{display:flex;flex-wrap:wrap;gap:5px}}
 .chip{{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #e0e7ff;padding:1px 8px;border-radius:11px;font-size:12px;margin:2px 3px 2px 0}}
 .chip.warn{{background:#fff7ed;color:#9a3412;border-color:#fed7aa}}
 .stats{{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0 6px}}
 .stat{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:120px}}
 .stat b{{display:block;font-size:21px}} .stat span{{font-size:12px;color:var(--mut)}}
 .muted{{color:#94a3b8}}
 .method{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
 .flow{{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:6px;font-size:13px}}
 .pill{{background:#f1f5f9;border:1px solid var(--line);border-radius:8px;padding:6px 11px}} .arr{{color:#94a3b8}}
 .formula{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#0f172a;color:#e2e8f0;padding:9px 12px;border-radius:8px;margin-top:11px;font-size:13px;display:inline-block}}
 .card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:16px 0;box-shadow:0 1px 2px rgba(0,0,0,.03)}}
 .chead{{display:flex;flex-direction:column;gap:4px;margin-bottom:6px}}
 .pid{{font-size:17px;font-weight:700}}
 .badge{{color:#fff;font-size:11px;font-weight:600;padding:2px 9px;border-radius:10px;margin-left:8px;vertical-align:middle}}
 .overall{{float:right;color:var(--mut);font-size:13px}} .overall b{{color:var(--ink);font-size:16px}}
 .tests{{color:var(--mut);font-size:13px}}
 .grid{{display:grid;grid-template-columns:1fr 1.25fr;gap:22px;margin-top:6px}}
 @media(max-width:820px){{.grid{{grid-template-columns:1fr}}}}
 .brief{{background:#fafafa;border-left:3px solid #cbd5e1;padding:9px 12px;border-radius:0 6px 6px 0;font-size:13.5px;color:#334155}}
 .check{{display:flex;gap:9px;padding:7px 0;border-bottom:1px solid #f1f5f9}}
 .mark{{font-weight:800;font-size:15px;line-height:1.3}}
 .ctext{{font-weight:600;font-size:13.5px}}
 .evid{{color:var(--mut);font-size:12.5px;margin-top:2px;font-style:italic}}
 .simmeta>div{{margin:4px 0;font-size:13px}} .simmeta b{{font-size:11px;text-transform:uppercase;color:var(--mut);margin-right:6px}}
 .transcript{{position:relative;border:1px solid var(--line);border-radius:8px;background:#fcfcfd}}
 .transcript pre{{margin:0;padding:12px 14px;white-space:pre-wrap;word-break:break-word;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#1e293b;max-height:none;overflow:auto}}
 .transcript.collapsed pre{{max-height:230px;overflow:hidden;-webkit-mask-image:linear-gradient(#000 70%,transparent)}}
 .more{{position:absolute;right:8px;bottom:8px;font-size:11px;border:1px solid var(--line);background:#fff;border-radius:7px;padding:3px 9px;cursor:pointer;color:var(--accent)}}
 .lens{{display:flex;align-items:center;gap:9px;margin:4px 0}}
 .lenslab{{width:62px;font-size:12px;color:var(--mut)}}
 .track{{flex:1;height:9px;background:#f1f5f9;border-radius:5px;overflow:hidden}} .fill{{display:block;height:100%}}
 .lensval{{width:26px;text-align:right;font-size:12.5px;font-weight:600}}
 .finding{{display:flex;gap:9px;padding:8px 0;border-top:1px solid #f1f5f9}}
 .sev{{color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:9px;height:fit-content;text-transform:uppercase}}
 .fmeta{{font-size:11.5px;color:#94a3b8}} .fix{{font-size:12.5px;color:#0f766e;margin-top:3px}}
 .distwrap{{margin:8px 0 4px}}
 .distrack{{position:relative;height:16px;background:linear-gradient(90deg,#fee2e2,#fef9c3 50%,#dcfce7);border-radius:8px}}
 .dot{{position:absolute;top:3px;width:10px;height:10px;border-radius:50%;background:#1e293b;opacity:.62;transform:translateX(-5px);border:1.5px solid #fff}}
 .medmark{{position:absolute;top:-3px;height:22px;width:2px;background:#0f172a;transform:translateX(-1px)}}
 .distlabels{{display:flex;justify-content:space-between;font-size:11px;color:var(--mut);margin-top:3px}}
 .staticcard,.diagcard{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:15px 18px;margin:12px 0}}
 .schead,.dhead{{font-size:14px;margin-bottom:8px}}
 .ftable{{width:100%;border-collapse:collapse;font-size:13px}} .ftable th{{text-align:left;color:var(--mut);font-size:11px;text-transform:uppercase;border-bottom:1px solid var(--line);padding:5px}}
 .ftable td{{padding:7px 5px;border-bottom:1px solid #f1f5f9;vertical-align:top}}
 .edit{{margin:9px 0}} .ehead{{font-size:12.5px;color:var(--mut);margin-bottom:3px}}
 .edit pre{{margin:0;padding:7px 10px;font:12px/1.45 ui-monospace,Menlo,monospace;white-space:pre-wrap;word-break:break-word;border-radius:6px}}
 .old{{background:#fef2f2;color:#991b1b}} .new{{background:#f0fdf4;color:#166534;margin-top:3px}}
 table.runs{{width:100%;border-collapse:collapse;font-size:13.5px;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}}
 table.runs th,table.runs td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left}}
 table.runs th{{background:#f8fafc;font-size:12px;color:var(--mut)}}
 .note{{font-size:12.5px;color:var(--mut);margin-top:8px}}
 a.anchor{{color:var(--accent);text-decoration:none;font-size:12.5px;margin-right:12px}}
</style></head><body><div class="wrap">

<h1>logbook-creator — real eval examples</h1>
<p class="sub">The actual persona simulations, transcripts, and judge scorecards that ran during the self-evaluation loops. Every transcript and score below is real output captured from the eval subagents — nothing here is hand-written.</p>

<div class="stats">
  <div class="stat"><b>350</b><span>eval subagents (run&nbsp;1: 84 · run&nbsp;2: 266)</span></div>
  <div class="stat"><b>6</b><span>hidden-state personas</span></div>
  <div class="stat"><b>240</b><span>sim+judge pairs across both runs</span></div>
  <div class="stat"><b>10.5M</b><span>subagent tokens</span></div>
</div>

<div class="method">
  <h4 style="margin-top:0">How each example was produced</h4>
  <div class="flow">
    <span class="pill"><b>Persona</b> — hidden-state brief, reveals facts only when asked</span><span class="arr">→</span>
    <span class="pill"><b>Sim</b> — one agent role-plays both sides, follows the real SKILL.md</span><span class="arr">→</span>
    <span class="pill"><b>Judge</b> — independent agent, never sees the skill, grades vs the contract</span>
  </div>
  <div class="formula">aggregate = 0.8 × mean(persona overall) + 0.2 × static&nbsp;consistency&nbsp;&nbsp;(0–5)</div>
</div>

<h2>Noise band — why the guard had to change</h2>
<p class="sub" style="margin-bottom:10px">Five identical evaluations of the <b>unchanged</b> skill (run&nbsp;2 calibration). The skill didn't change — the score did. That spread is the noise floor every "improvement" must beat.</p>
<div class="method">
  {dist_dots([4.01,3.91,3.87,3.87,4.15],0.12).replace('distwrap','distwrap')}
  <div class="note">aggregate baseline: <b>median 3.91</b>, sd 0.12, <b>range 0.28</b>. Run&nbsp;1's entire story — a +0.13 "win" and 0.11–0.34 "regressions" — fits inside this band. The per-persona dots on each card below show where the noise lives: <b>crisp-expert</b> alone swings a full point (sd&nbsp;0.45).</div>
</div>

<h2>The six personas <span style="font-weight:400;font-size:13px;color:var(--mut)">— real transcript + real scorecard each</span></h2>
<div style="margin-bottom:6px">{''.join(f'<a class="anchor" href="#{p}">{esc(PMETA[p]["title"])}</a>' for p in ORDER)}</div>
{cards}

<h2>Static-audit arm <span style="font-weight:400;font-size:13px;color:var(--mut)">— internal-consistency findings (real)</span></h2>
{static_block()}

<h2>Diagnose arm <span style="font-weight:400;font-size:13px;color:var(--mut)">— the one above-noise win (+0.20)</span></h2>
{diagnose_block()}

<h2>Both runs</h2>
<table class="runs">
<thead><tr><th>run</th><th>guard</th><th>baseline → final (median)</th><th>accepted</th><th>note</th></tr></thead>
<tbody>
<tr><td>wf_91ee9671</td><td>single sample</td><td>3.97 → 4.09</td><td>1 / 5</td><td>verdicts dominated by noise</td></tr>
<tr><td>wf_db60e4d2</td><td>median&nbsp;of&nbsp;3</td><td>3.91 → 4.14</td><td>3 / 5</td><td>only R1 (+0.20) clears the noise band; R3/R4 within residual noise</td></tr>
</tbody></table>
<p class="note">Generated from <code>plugins/logbook-creator/evals/eval-examples.data.json</code>, extracted from the workflow subagent transcripts. Representative example per persona = the captured run with the richest transcript.</p>

</div></body></html>'''

outp='/Users/dmytro/projects/logbooks/plugins/logbook-creator/evals/eval-examples.html'
open(outp,'w').write(HTML)
print('wrote', outp, os.path.getsize(outp), 'bytes')
