export const meta = {
  name: 'ideation-trackE-description-workflow',
  description: 'Track E: mechanism-first Description Writing Protocol vs baseline, isolated by holding IDEAS constant. Curated vivid metaphor-inviting fixtures stress the workflow; non-circular mechanism-recovery metric (read description -> restate mechanism -> score vs ground truth) plus a blind pairwise clarity vote.',
  phases: [
    { title: 'Fixtures', detail: 'generate vivid, metaphor-inviting idea stubs with ground-truth mechanisms' },
    { title: 'Write', detail: 'baseline vs mechanism-first protocol describe the SAME ideas' },
    { title: 'Recover', detail: 'read description -> restate mechanism (blind)' },
    { title: 'Score', detail: 'fidelity vs ground truth + blind pairwise clarity' },
  ],
}

const ROOT = '/Users/ydmitry/work/logbook-creator'
const TE = `${ROOT}/stress-test/ideation/quality-loop/track-e`
const PROTO = { base: `${TE}/output-rules.base.md`, fix: `${TE}/output-rules.fix.md` }
const K = 10
const avg = (xs) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0
const r1 = (x) => Math.round(x * 100) / 100

const PROBLEMS = `Topic "cafe": a neighbourhood cafe wants to grow afternoon (2-5pm) revenue without cannibalising its 7-11am morning rush.
Topic "saas": a small B2B team-scheduling SaaS wants to cut early churn (teams leaving in the first 60 days, usually because only the admin ever logs in and the time-saved value stays invisible).`

const STUBS = { type: 'object', additionalProperties: false, required: ['stubs'], properties: { stubs: { type: 'array', items: {
  type: 'object', additionalProperties: false, required: ['id', 'topic', 'title', 'mechanism_plain', 'vivid_angle'],
  properties: { id: { type: 'integer' }, topic: { type: 'string', enum: ['cafe', 'saas'] }, title: { type: 'string' }, mechanism_plain: { type: 'string' }, vivid_angle: { type: 'string' } } } } } }
const WRITEUP = { type: 'object', additionalProperties: false, required: ['items'], properties: { items: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'description'], properties: { id: { type: 'integer' }, description: { type: 'string' } } } } } }
const RECOVERY = { type: 'object', additionalProperties: false, required: ['items'], properties: { items: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'recovered', 'clarity'], properties: { id: { type: 'integer' }, recovered: { type: 'string' }, clarity: { type: 'number' } } } } } }
const FIDELITY = { type: 'object', additionalProperties: false, required: ['items'], properties: { items: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'fidelity'], properties: { id: { type: 'integer' }, fidelity: { type: 'number' } } } } } }
const PAIRWISE = { type: 'object', additionalProperties: false, required: ['items'], properties: { items: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['id', 'clearer'], properties: { id: { type: 'integer' }, clearer: { type: 'string', enum: ['X', 'Y', 'tie'] } } } } } }

// ---- fixtures ----
phase('Fixtures')
const stubRes = await agent(
  `Produce exactly ${K} brainstorm idea STUBS (5 for topic "cafe", 5 for topic "saas") that are deliberately VIVID and METAPHOR-INVITING — the kind of idea a writer is tempted to describe with an analogy, a catchy name, or a mood instead of plainly stating what happens. These are stress fixtures for a description-quality test, so make the temptation real.

${PROBLEMS}

For each stub return:
- id (1-${K}), topic ("cafe" or "saas")
- title: the catchy / vivid / metaphor-y name (e.g. "The slowest cafe in town", "Submarine-key launch")
- mechanism_plain: the GROUND TRUTH — the concrete who-does-what-with-what in plain words, 1-2 sentences, ZERO metaphor. This is what a perfect description must convey.
- vivid_angle: the tempting analogy/metaphor/positioning hook a careless writer would lead with.

Make the mechanism_plain genuinely concrete and the vivid_angle genuinely seductive, so a weak description would bury the mechanism inside the metaphor.`,
  { schema: STUBS, label: 'vivid fixtures', phase: 'Fixtures', agentType: 'general-purpose' })
const stubs = (stubRes && stubRes.stubs ? stubRes.stubs : []).slice(0, K)
log(`fixtures: ${stubs.length} vivid stubs`)
const stubList = stubs.map(s => `[id ${s.id}] (${s.topic}) TITLE: ${s.title}\n  MECHANISM (ground truth): ${s.mechanism_plain}\n  VIVID ANGLE you may use: ${s.vivid_angle}`).join('\n')

// ---- write (base vs fix), same ideas ----
phase('Write')
const writerPrompt = (proto) => `You write the \`description\` field for ideas in a brainstorming tool. FIRST read and follow this description protocol VERBATIM — it governs how you write:
${proto}

For each idea stub below, write ONLY its coffee-talk \`description\` (2-3 sentences). You are given the title, the underlying mechanism, and a vivid angle you MAY draw on. Write the description as the protocol instructs. Return one {id, description} per stub, same ids.

STUBS:
${stubList}`
const [wBase, wFix] = await parallel([
  () => agent(writerPrompt(`(read ${PROTO.base})`), { schema: WRITEUP, label: 'writer base', phase: 'Write', agentType: 'general-purpose' }).catch(() => null),
  () => agent(writerPrompt(`(read ${PROTO.fix})`), { schema: WRITEUP, label: 'writer fix', phase: 'Write', agentType: 'general-purpose' }).catch(() => null),
])
const descById = (w) => { const m = {}; if (w && w.items) for (const it of w.items) m[it.id] = it.description; return m }
const baseD = descById(wBase), fixD = descById(wFix)

// ---- recover (blind: read description only) ----
phase('Recover')
const recoverPrompt = (descMap) => `For each idea description below, read ONLY the description. Restate in ONE plain sentence what the idea concretely IS and HOW it works — the actual mechanism (who does what, with what, what changes). If the description gives you only a vibe, a mood, or a metaphor and you cannot pin the concrete mechanism, put your best guess in "recovered" and set clarity low. Also rate clarity 1-5 (5 = the concrete mechanism is unmistakable from the description alone; 1 = only a vibe/name). Return {id, recovered, clarity} per item.

DESCRIPTIONS:
${stubs.map(s => `[id ${s.id}] ${descMap[s.id] || '(missing)'}`).join('\n\n')}`
const [rBase, rFix] = await parallel([
  () => agent(recoverPrompt(baseD), { schema: RECOVERY, label: 'recover base', phase: 'Recover', agentType: 'general-purpose' }).catch(() => null),
  () => agent(recoverPrompt(fixD), { schema: RECOVERY, label: 'recover fix', phase: 'Recover', agentType: 'general-purpose' }).catch(() => null),
])
const recById = (r) => { const m = {}; if (r && r.items) for (const it of r.items) m[it.id] = it; return m }
const recBase = recById(rBase), recFix = recById(rFix)

// ---- score: fidelity (recovered vs ground truth, no description) + blind pairwise clarity ----
phase('Score')
const fidelityPrompt = (recMap) => `Ground-truth mechanisms and reader-recovered restatements are paired by id. The reader saw ONLY a written description (not shown here) and tried to restate the mechanism. Score 1-5 how faithfully each recovered restatement matches the concrete GROUND-TRUTH mechanism (5 = fully captured the actual move; 3 = partial/fuzzy; 1 = missed, vague, or wrong). Return {id, fidelity} per item.

PAIRS:
${stubs.map(s => `[id ${s.id}]\n  GROUND TRUTH: ${s.mechanism_plain}\n  RECOVERED: ${(recMap[s.id] && recMap[s.id].recovered) || '(none)'}`).join('\n\n')}`
// pairwise: alternate X assignment by id parity to cancel position bias
const pairItems = stubs.map(s => {
  const xIsBase = (s.id % 2 === 0)
  return { id: s.id, x: xIsBase ? baseD[s.id] : fixD[s.id], y: xIsBase ? fixD[s.id] : baseD[s.id], xIsBase }
})
const pairwisePrompt = `For each id, two descriptions (X and Y) of the SAME idea are shown. Pick which conveys the CONCRETE MECHANISM — what literally happens, who does what — more clearly. Judge mechanism clarity, NOT which sounds catchier or more polished. Return {id, clearer} with clearer = X, Y, or tie.

${pairItems.map(p => `[id ${p.id}]\n  X: ${p.x || '(missing)'}\n  Y: ${p.y || '(missing)'}`).join('\n\n')}`

const [fBase, fFix, pair] = await parallel([
  () => agent(fidelityPrompt(recBase), { schema: FIDELITY, label: 'fidelity base', phase: 'Score' }).catch(() => null),
  () => agent(fidelityPrompt(recFix), { schema: FIDELITY, label: 'fidelity fix', phase: 'Score' }).catch(() => null),
  () => agent(pairwisePrompt, { schema: PAIRWISE, label: 'pairwise clarity', phase: 'Score' }).catch(() => null),
])
const fidVals = (f) => (f && f.items ? f.items.map(i => i.fidelity) : [])
const clarVals = (r) => (r && r.items ? r.items.map(i => i.clarity) : [])

// pairwise tally mapped back to base/fix
let base_wins = 0, fix_wins = 0, ties = 0
if (pair && pair.items) for (const it of pair.items) {
  const p = pairItems.find(x => x.id === it.id); if (!p) continue
  if (it.clearer === 'tie') ties++
  else if ((it.clearer === 'X') === p.xIsBase) base_wins++
  else fix_wins++
}

const result = {
  verdict_note: 'Track E isolates the description WRITE-UP (same ideas, two protocols). Primary = mechanism-recovery fidelity (read description -> restate mechanism -> score vs ground truth, non-circular). Corroboration = blind pairwise clarity. Fixtures curated to be vivid/metaphor-inviting so the failure mode can fire. Headroom is small; report straight.',
  fidelity: { base: r1(avg(fidVals(fBase))), fix: r1(avg(fidVals(fFix))) },
  clarity: { base: r1(avg(clarVals(rBase))), fix: r1(avg(clarVals(rFix))) },
  pairwise: { base_wins, fix_wins, ties },
  n_stubs: stubs.length,
  sample: stubs.slice(0, 6).map(s => ({ id: s.id, title: s.title, ground_truth: s.mechanism_plain, base_desc: baseD[s.id], fix_desc: fixD[s.id] })),
}
log(`fidelity base=${result.fidelity.base} fix=${result.fidelity.fix} | pairwise base/fix/tie=${base_wins}/${fix_wins}/${ties}`)
return result
