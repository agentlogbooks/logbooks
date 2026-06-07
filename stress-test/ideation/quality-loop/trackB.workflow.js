export const meta = {
  name: 'ideation-quality-loop-trackB',
  description: 'Track B: 5-round render-judge-improve loop on view.dynamic.html (the dynamic-viz prototype), with a blind baseline-vs-final A/B as the honest result',
  phases: [
    { title: 'Render', detail: 'screenshot the prototype across states via the replay harness' },
    { title: 'Judge', detail: 'score UX/visual + code quality, list fixable issues' },
    { title: 'Improve', detail: 'edit view.dynamic.html to fix top issues (rounds 1-4)' },
    { title: 'Blind', detail: 'blind A/B baseline (round-0) vs final, position-swapped' },
  ],
}

const ROOT = '/Users/ydmitry/work/logbook-creator'
const WS = `${ROOT}/stress-test/ideation`
const HTML = `${WS}/view.dynamic.html`
const RDIR = `${WS}/quality-loop/track-b/rounds`
const STATES = ['empty', 'framing', 'scored', 'churn', '80']
const avg = (xs) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0
const r1 = (x) => Math.round(x * 100) / 100

const RENDER = {
  type: 'object', additionalProperties: false, required: ['ok', 'shots', 'note'],
  properties: { ok: { type: 'boolean' }, shots: { type: 'array', items: { type: 'string' } }, note: { type: 'string' } },
}
const TBJUDGE = {
  type: 'object', additionalProperties: false, required: ['ux', 'code', 'per_state', 'top_issues'],
  properties: {
    ux: { type: 'number', description: 'overall visual/UX quality 1-5: winners clarity, scannability at 80, motion-when-populated, useful empty/framing state, clean cut handling' },
    code: { type: 'number', description: 'code quality 1-5: clean vanilla JS/CSS, no libraries, valid, safe drop-in on the same SSE contract' },
    per_state: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['state', 'score', 'note'], properties: { state: { type: 'string' }, score: { type: 'number' }, note: { type: 'string' } } } },
    top_issues: { type: 'array', items: { type: 'string' }, description: '2-3 concrete, fixable issues, highest-impact first' },
  },
}
const TBBLIND = {
  type: 'object', additionalProperties: false, required: ['ux_X', 'ux_Y', 'better_ux', 'reason'],
  properties: { ux_X: { type: 'number' }, ux_Y: { type: 'number' }, better_ux: { type: 'string', enum: ['X', 'Y', 'tie'] }, reason: { type: 'string' } },
}

const renderPrompt = (r, port, htmlPath, outDir) => `You render the ideation live-wall prototype to screenshots using the replay harness. Run these EXACT bash steps (the harness serves the HTML + replays an event stream over SSE):

mkdir -p ${outDir}
cd ${WS}
for s in ${STATES.join(' ')}; do
  python3 wall_replay.py --events scenarios/state_$s.jsonl --html ${htmlPath} --port ${port} --cadence 0 > /tmp/tb-${port}.log 2>&1 &
  PID=$!
  sleep 1.6
  playwright screenshot "http://127.0.0.1:${port}" "${outDir}/$s.png" --full-page --wait-for-timeout 2400 --browser chromium >/dev/null 2>&1
  kill $PID 2>/dev/null; wait $PID 2>/dev/null
done
ls -la ${outDir}

Then return: ok=true if all 5 PNGs exist and are non-trivial in size (>5KB), shots = the 5 absolute PNG paths, note = anything odd (empty board, errors in the log). If a screenshot is missing or tiny, ok=false and say which.`

const judgePrompt = (shots, ok, htmlPath) => `You are a UX + front-end judge evaluating a live "idea wall" web view (a real-time sticky-note board for a brainstorming tool). ${ok ? `Look at these rendered screenshots (one per state):\n${shots.map(s => `- ${s}`).join('\n')}\n\nUse the Read tool to view each PNG.` : `Rendering FAILED this round — judge from the code only and flag that the render was broken (likely a regression from the last edit).`}

Also Read the source: ${htmlPath}

Score 1-5 (3=average, 5=rare):
- ux: winners/ranked ideas instantly visible (scored, 80 states); 80-idea board scannable not an undifferentiated scroll; feels dynamic when populated (reorder/heat/rank/pulse — judge motion from the code + states); empty/framing state useful not dead; cut ideas handled cleanly (churn).
- code: clean vanilla JS/CSS, NO external libraries (a library is an automatic code<=2), valid HTML, safe drop-in on the same SSE event contract (handlers: session_started, plan_set, phase_started, op_started/finished, checkpoint_*, idea_generated/scored/kept/cut/ranked, session_complete).

Give per_state scores+notes for: ${STATES.join(', ')}. Then list the top 2-3 CONCRETE, FIXABLE issues, highest-impact first (e.g. "rank badge unreadable on dark cut card", "80-board has no section break"). Prioritise real visual/interaction problems over nitpicks.`

const improvePrompt = (issues, htmlPath, r) => `You are improving a live "idea wall" web view. Edit this file IN PLACE: ${htmlPath}

A judge flagged these top issues (fix the highest-impact ones):
${issues.map(i => `- ${i}`).join('\n')}

HARD CONSTRAINTS (violating these is a regression):
- VANILLA only — plain HTML/CSS/JS. NO external libraries, frameworks, CDNs, or build steps. Adding any library is a failure.
- Stay a DROP-IN for live/view.html: keep the exact SSE contract — do NOT rename or drop any event handler (session_started, plan_set, phase_started, op_started, op_finished, checkpoint_reached, checkpoint_resolved, idea_generated, idea_scored, idea_kept, idea_cut, idea_ranked, session_complete). The page must still connect to new EventSource('/events').
- Keep the dark sticky-note aesthetic and the existing dynamic behaviors (FLIP reorder-on-score, score heat, rank badges, compost tray, activity line) — improve them, don't strip them.
- Keep it ONE self-contained .html file. Valid HTML — unbalanced tags or a JS syntax error will blank the board.
- Make focused edits targeting the flagged issues; don't rewrite wholesale.

After editing, run: cp ${htmlPath} ${RDIR}/round-${r}.html   (snapshot this round)
Then return a 3-6 line changelog: what you changed and which issue each edit fixes.`

// ---- loop ----
const rounds = []
let lastShots = []
for (let r = 1; r <= 5; r++) {
  const outDir = `${RDIR}/round-${r}`
  const port = 7950 + r
  log(`Round ${r}/5 — render @ port ${port}`)
  const rend = await agent(renderPrompt(r, port, HTML, outDir), { schema: RENDER, label: `render r${r}`, phase: 'Render', agentType: 'general-purpose' }).catch(() => null)
  const ok = !!(rend && rend.ok)
  const shots = ok && rend.shots && rend.shots.length ? rend.shots : STATES.map(s => `${outDir}/${s}.png`)
  if (ok) lastShots = shots
  if (!ok) log(`  render r${r} degraded — judging code only`)

  const j = await agent(judgePrompt(shots, ok, HTML), { schema: TBJUDGE, label: `judge r${r}`, phase: 'Judge', agentType: 'general-purpose' }).catch(() => null)
  if (j) { rounds.push({ round: r, ux: r1(j.ux), code: r1(j.code), render_ok: ok, top_issues: j.top_issues }); log(`  round ${r}: ux=${r1(j.ux)} code=${r1(j.code)} render_ok=${ok}`) }
  else { rounds.push({ round: r, ux: null, code: null, render_ok: ok, top_issues: [] }); log(`  round ${r}: judge failed`) }

  if (r < 5) {
    const issues = (j && j.top_issues && j.top_issues.length) ? j.top_issues : ['general polish: improve scannability and motion-when-populated']
    await agent(improvePrompt(issues, HTML, r), { label: `improve r${r}→${r + 1}`, phase: 'Improve', agentType: 'general-purpose' }).catch(() => log(`  improve r${r} failed — html unchanged`))
  }
}

// ---- blind A/B: baseline round-0 vs final, position-swapped ----
log('Blind A/B: render baseline (round-0) and final, then compare blind')
const baseDir = `${RDIR}/blind-baseline`, finalDir = `${RDIR}/blind-final`
const [baseR, finalR] = await parallel([
  () => agent(renderPrompt(0, 7961, `${RDIR}/round-0.html`, baseDir), { schema: RENDER, label: 'render baseline', phase: 'Render', agentType: 'general-purpose' }).catch(() => null),
  () => agent(renderPrompt(99, 7962, HTML, finalDir), { schema: RENDER, label: 'render final', phase: 'Render', agentType: 'general-purpose' }).catch(() => null),
])
const baseShots = STATES.map(s => `${baseDir}/${s}.png`)
const finalShots = STATES.map(s => `${finalDir}/${s}.png`)
const blindPrompt = (xShots, yShots) => `Two anonymous versions of a live "idea wall" web view are rendered below as screenshot sets — Set X and Set Y — across the same states (${STATES.join(', ')}). You know nothing about how either was produced. Judge purely on visual/UX quality: winners instantly visible, 80-idea board scannable, feels dynamic when populated, useful empty/framing state, clean cut handling.

Use the Read tool to view every PNG.
SET X: ${xShots.join(', ')}
SET Y: ${yShots.join(', ')}

Rate each set's ux (1-5), say which has higher ux (X, Y, or tie), and why in 2-3 sentences. Do not assume either is meant to be better.`
const [abA, abB] = await parallel([
  () => agent(blindPrompt(baseShots, finalShots), { schema: TBBLIND, label: 'blind X=base Y=final', phase: 'Blind', agentType: 'general-purpose' }).catch(() => null),
  () => agent(blindPrompt(finalShots, baseShots), { schema: TBBLIND, label: 'blind X=final Y=base', phase: 'Blind', agentType: 'general-purpose' }).catch(() => null),
])
const final_ux = r1(avg([abA && abA.ux_Y, abB && abB.ux_X].filter(v => v != null)))
const base_ux = r1(avg([abA && abA.ux_X, abB && abB.ux_Y].filter(v => v != null)))
const prefers_final = [
  abA ? (abA.better_ux === 'Y' ? 'final' : abA.better_ux === 'X' ? 'baseline' : 'tie') : null,
  abB ? (abB.better_ux === 'X' ? 'final' : abB.better_ux === 'Y' ? 'baseline' : 'tie') : null,
].filter(Boolean)

return {
  trajectory: rounds.map(r => ({ round: r.round, ux: r.ux, code: r.code, render_ok: r.render_ok })),
  blind_ab: { baseline_ux: base_ux, final_ux: final_ux, prefers: prefers_final, reasons: [abA && abA.reason, abB && abB.reason].filter(Boolean) },
  issues_by_round: rounds.map(r => ({ round: r.round, top_issues: r.top_issues })),
}
