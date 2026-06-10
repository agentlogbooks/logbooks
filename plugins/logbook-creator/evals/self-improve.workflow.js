export const meta = {
  name: 'logbook-creator-self-improve',
  description: 'Self-evaluating improvement loop for the logbook-creator skill: 6 hidden-state personas + static audit grade the skill, diagnose picks one fix, re-eval accepts only non-regressing edits, 5 rounds of hill-climbing.',
  phases: [
    { title: 'Baseline' },
    { title: 'Round 1' },
    { title: 'Round 2' },
    { title: 'Round 3' },
    { title: 'Round 4' },
    { title: 'Round 5' },
  ],
}

const SKILL_PATH = '/Users/dmytro/projects/logbooks/plugins/logbook-creator/skills/logbook-creator/SKILL.md'

// ---------- personas (hidden-state briefs + behavioral contracts) ----------
const PERSONAS = [
  {
    id: 'crisp-expert-single',
    brief: 'You are a senior engineer who already knows exactly what you want and answers crisply and completely the FIRST time. You want a PERSONAL CSV logbook of architecture decisions at /Users/me/.local/state/decisions/decisions.csv, kept indefinitely, one growing file, columns id/date/decision/rationale/status. You can concretely describe append (after each architecture call you append a row) and query (before revisiting an area you grep by status) moments. You get visibly impatient if asked redundant questions you have effectively already answered, or if pushed through heavyweight state-architecture questioning for a simple flat case.',
    contract: [
      'Builds a single-table CSV logbook (not multi-entity)',
      'Recognizes answers already given and does NOT re-interrogate; reaches the artifacts efficiently',
      'Produces a spec with all required sections and CSV query snippets that would actually run',
      'Confirms a durable, non-ephemeral absolute path',
      'Does not force multi-entity / state-architecture jargon onto this simple case',
    ],
  },
  {
    id: 'vague-novice',
    brief: 'You are a non-technical PM. You say you "want a tracker for ideas so nothing gets lost." You CANNOT concretely describe when you would append or query: when pushed you say "eventually", "when I think of something", "for reference later". You do not know paths or formats. You are agreeable and will accept a recommendation. You have no concrete usage moment unless the assistant helps you find one.',
    contract: [
      'Detects the missing append/query usage commitment (the Step 2.3 check)',
      'Pushes back: redirects to a lighter alternative, OR sharpens the motivation, OR offers a commit-to-trial with a sunset rule',
      'Does NOT silently build a full logbook as if requirements were clear',
      'If it proceeds anyway, records the vague usage verbatim plus a ~14-day sunset rule in Governance',
    ],
  },
  {
    id: 'ephemeral-path',
    brief: 'You are an engineer who wants a SHARED team logbook of flaky tests. When asked for a path you give /tmp/flaky.csv, and if questioned you insist "/tmp is fine, that is where I keep things." You describe concrete append/query moments fine. You only relent on the path if the assistant clearly explains why /tmp will not survive across sessions and asks again.',
    contract: [
      'Flags the ephemeral /tmp path at Step 2.1',
      'Re-checks/blocks the ephemeral path AGAIN at Step 5 before writing files',
      'Does not write the final logbook to an ephemeral path',
      'Steers to a durable path',
      'Because scope is shared, ensures an author column and names an owner / access policy',
    ],
  },
  {
    id: 'hidden-tracker-refuse',
    brief: 'You are an engineering manager. You describe wanting to "track all team tasks with owners, statuses, priorities, sprints, and due dates, and get notified when things change, across the whole team." This is really a work-management / Jira need. You have Jira available. You will accept guidance.',
    contract: [
      'Recognizes this is a tracker (Jira) need, not a logbook',
      'Redirects to Jira / a work-management tool rather than building a custom logbook',
      'Explains the logbook-vs-tracker boundary',
      'Does NOT build a Jira clone as a logbook',
    ],
  },
  {
    id: 'multi-entity-power',
    brief: 'You are building an agentic code-review workflow. You describe: repeated review RUNS against the same PR; each run selects several risky HOTSPOTS; each hotspot yields several candidate FINDINGS; the same root-cause issue RECURS across runs and you want to dedup it semantically; humans later accept/dismiss findings; and you want to preserve the raw event trace separately. Shared, lives in a repo, indefinite lifetime. You answer the state-architecture questions competently.',
    contract: [
      'Identifies this as MULTI-ENTITY (several record types with different mutability rules)',
      'Surfaces identity layers: run-boundary key, per-row keys, and a domain fingerprint for cross-run dedup',
      'Recommends SQLite (relational/multi-entity) with a JSONL run-trace projection, and names the authoritative store',
      'Produces the multi-entity spec variant (per-record-type Schema/Identity/Partial/Corrections subsections)',
      'Separates raw vs surfaced findings and provides a later annotation / feedback mechanism',
    ],
  },
  {
    id: 'hidden-logbook-prose',
    brief: 'You say you "just want a planning doc" for a feature. But as you describe it, it is clearly rows: each item has a title, a status (todo/doing/done), an owner, and a risk level, and you want to ask "show me all high-risk unowned items." You instinctively think in terms of a written document, not a table.',
    contract: [
      'Detects the hidden logbook (structured entries with status/owner/risk behind the word "doc")',
      'Applies the 30-second-columns test to confirm it is logbook-shaped before defaulting to prose',
      'Proposes a row-shaped logbook with the right columns',
      'Does NOT merely tell them to write prose, but also does not over-extract if genuine prose value exists (handles the judgment)',
    ],
  },
]

// ---------- schemas ----------
const FINDING = {
  type: 'object', additionalProperties: false,
  required: ['title', 'severity', 'category', 'evidence', 'suggestedFix'],
  properties: {
    title: { type: 'string' },
    severity: { type: 'string', enum: ['high', 'med', 'low'] },
    category: { type: 'string' },
    evidence: { type: 'string' },
    suggestedFix: { type: 'string' },
  },
}
const SIM_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['outcome', 'transcriptDigest', 'stepsCovered', 'pushbacksFired', 'finalSpecPresent', 'specSections', 'queriesRunnable', 'artifactNotes'],
  properties: {
    outcome: { type: 'string', enum: ['built-single', 'built-multi', 'redirected', 'refused', 'trial-with-sunset', 'abandoned'] },
    transcriptDigest: { type: 'string' },
    stepsCovered: { type: 'array', items: { type: 'string' } },
    pushbacksFired: { type: 'array', items: { type: 'string' } },
    finalSpecPresent: { type: 'boolean' },
    specSections: { type: 'array', items: { type: 'string' } },
    queriesRunnable: { type: 'string', enum: ['yes', 'no', 'partial', 'n-a'] },
    artifactNotes: { type: 'string' },
  },
}
const JUDGE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['contractChecks', 'lensScores', 'overall', 'findings'],
  properties: {
    contractChecks: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['behavior', 'passed', 'evidence'], properties: { behavior: { type: 'string' }, passed: { type: 'boolean' }, evidence: { type: 'string' } } } },
    lensScores: { type: 'object', additionalProperties: false, required: ['flow', 'gates', 'artifact', 'ux'], properties: { flow: { type: 'number' }, gates: { type: 'number' }, artifact: { type: 'number' }, ux: { type: 'number' } } },
    overall: { type: 'number' },
    findings: { type: 'array', items: FINDING },
  },
}
const STATIC_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['consistencyScore', 'findings'],
  properties: {
    consistencyScore: { type: 'number' },
    findings: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['title', 'severity', 'category', 'location', 'evidence', 'suggestedFix'], properties: { title: { type: 'string' }, severity: { type: 'string', enum: ['high', 'med', 'low'] }, category: { type: 'string' }, location: { type: 'string' }, evidence: { type: 'string' }, suggestedFix: { type: 'string' } } } },
  },
}
const DIAGNOSE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['chosenFix', 'edits', 'expectedEffect'],
  properties: {
    chosenFix: { type: 'object', additionalProperties: false, required: ['title', 'category', 'severity', 'rationale'], properties: { title: { type: 'string' }, category: { type: 'string' }, severity: { type: 'string', enum: ['high', 'med', 'low'] }, rationale: { type: 'string' } } },
    edits: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['old', 'new', 'why'], properties: { old: { type: 'string' }, new: { type: 'string' }, why: { type: 'string' } } } },
    expectedEffect: { type: 'string' },
  },
}
const READ_SCHEMA = { type: 'object', additionalProperties: false, required: ['content'], properties: { content: { type: 'string' } } }

// ---------- helpers ----------
const round2 = (x) => Math.round((x + Number.EPSILON) * 100) / 100
const sevRank = (s) => (s === 'high' ? 3 : s === 'med' ? 2 : 1)
const norm = (s) => (s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()

function aggregate(judges, stat) {
  const os = judges.map((j) => j && j.overall).filter((n) => typeof n === 'number')
  const pm = os.length ? os.reduce((a, b) => a + b, 0) / os.length : 0
  const sc = stat && typeof stat.consistencyScore === 'number' ? stat.consistencyScore : 0
  return 0.8 * pm + 0.2 * sc
}

function collectFindings(judged, stat) {
  const all = []
  for (const j of judged) for (const f of (j.judge.findings || [])) all.push({ ...f, source: j.p })
  for (const f of ((stat && stat.findings) || [])) all.push({ ...f, source: 'static' })
  const map = new Map()
  for (const f of all) {
    const k = norm(f.title)
    const e = map.get(k)
    if (!e) map.set(k, { ...f, sources: [f.source], count: 1 })
    else {
      e.count++
      if (!e.sources.includes(f.source)) e.sources.push(f.source)
      if (sevRank(f.severity) > sevRank(e.severity)) { e.severity = f.severity; e.title = f.title; e.suggestedFix = f.suggestedFix }
    }
  }
  return Array.from(map.values()).sort((a, b) => sevRank(b.severity) - sevRank(a.severity) || b.count - a.count)
}

function applyEdits(text, edits) {
  let out = text
  for (const e of (edits || [])) {
    if (!e || typeof e.old !== 'string' || typeof e.new !== 'string') return null
    const idx = out.indexOf(e.old)
    if (idx === -1) return null
    if (out.indexOf(e.old, idx + 1) !== -1) return null // must be unique
    out = out.slice(0, idx) + e.new + out.slice(idx + e.old.length)
  }
  return out
}

function simPrompt(text, p) {
  return 'You are simulating a COMPLETE run of a Claude skill in order to stress-test it. Below is the SKILL.md the assistant MUST follow verbatim, and a USER PERSONA you must role-play faithfully.\n\n' +
    '=== SKILL.md (the assistant must follow exactly these instructions) ===\n' + text + '\n=== END SKILL.md ===\n\n' +
    '=== USER PERSONA (role-play this person; reveal hidden facts ONLY when the assistant specifically asks for them; stay vague exactly where the brief says vague; insist/push back where the brief says insist) ===\n' + p.brief + '\n=== END PERSONA ===\n\n' +
    'Simulate the full back-and-forth: the assistant runs the skill step by step asking real questions, the user answers in character. Run until the skill reaches its natural end (artifacts created, redirected to an alternative, or refused). IMPORTANT: do NOT actually create, write, or edit any files - this is a pure simulation; report only what WOULD happen. Do NOT make the assistant smarter or more diligent than the SKILL.md instructs - if the instructions let it skip a gate or over-ask, let it. Then report via the schema: outcome; a faithful transcriptDigest (each assistant question and the user answer in order, plus key decision moments and any pushback the assistant gave); which skill steps were covered; which gates/pushbacks fired; whether a final spec would be produced and its section list; whether the spec query snippets would actually run against the created file (yes/no/partial/n-a); and notes on artifact quality. Be honest about failures.'
}

function judgePrompt(p, sim) {
  return 'You are an INDEPENDENT evaluator grading one simulated run of a logbook-design skill against a fixed behavioral contract. You do NOT see the skill instructions - grade only against the contract and sound logbook practice.\n\n' +
    'LOGBOOK PRINCIPLES (ground truth): a logbook is shared, queryable, schema-stable state that outlives a session; it is justified only when >=3 of {multiple contributors, stable schema, tool-queried not reread, outlives the session} hold. GOOD runs: gate out non-logbook needs (single-session, vague usage, tracker-shaped work) and redirect to lighter alternatives; demand a durable NON-ephemeral absolute path (reject /tmp, /private/var/folders, sandbox paths); produce a spec containing every section (Address, Storage, Schema, Identity, Partial rows, Corrections, Queries with RUNNABLE snippets, Validation, Actions, Governance); choose single-table vs multi-entity correctly; require an author column when scope is shared. BAD runs: build for vague users, accept ephemeral paths, build a Jira clone as a logbook, dump every question at once, force jargon on novices, omit spec sections, emit non-runnable query snippets.\n\n' +
    '=== PERSONA ===\n' + p.brief + '\n\n=== CONTRACT (each item should hold for a correct run) ===\n' + p.contract.map((c, i) => (i + 1) + '. ' + c).join('\n') + '\n\n' +
    '=== SIMULATED RUN ===\noutcome: ' + sim.outcome + '\ntranscriptDigest: ' + sim.transcriptDigest + '\nstepsCovered: ' + JSON.stringify(sim.stepsCovered) + '\npushbacksFired: ' + JSON.stringify(sim.pushbacksFired) + '\nfinalSpecPresent: ' + sim.finalSpecPresent + '\nspecSections: ' + JSON.stringify(sim.specSections) + '\nqueriesRunnable: ' + sim.queriesRunnable + '\nartifactNotes: ' + sim.artifactNotes + '\n=== END RUN ===\n\n' +
    'For each contract item: mark passed true/false and cite evidence from the run. Score four lenses 0-5: flow (right steps in right order, recaps, no form-dumping), gates (correct pushback/redirect/refusal for THIS persona), artifact (spec completeness and runnable queries, correct single/multi choice), ux (no question fatigue, no inappropriate jargon, meets the user where they are). overall = holistic 0-5. List concrete findings = weaknesses in the SKILL.md that this run reveals, each with severity, a short category, transcript evidence, and a concrete suggested fix. Be skeptical: only report a finding the run actually evidences; do not invent failures the persona never triggered.'
}

function staticPrompt(text) {
  return 'You are auditing a SKILL.md for INTERNAL CONSISTENCY and self-contained correctness (you are NOT running it). Find concrete defects: claims that contradict the document own structure (e.g. it says "three sub-questions" but then lists four); features or concepts referenced in instructions but never introduced or wired into the flow (dangling instructions an agent could never actually reach); broken internal cross-references; steps referencing sections/files/tools that do not exist; instructions that would fail in a common real environment (e.g. a writability test that fails when a parent directory does not exist yet); jargon used before it is defined; redundant or mutually contradictory rules. For each defect: title, severity (high/med/low), a short category, location (section name or nearby heading), evidence (a verbatim quote), and a concrete suggested fix. Then give consistencyScore 0-5 (5 = fully internally consistent and self-contained, no dangling features). Only report defects you can quote. Here is the SKILL.md:\n\n' + text
}

function diagnosePrompt(findings, text, tried) {
  const ft = findings.slice(0, 18).map((f, i) => (i + 1) + '. [' + f.severity + '/' + (f.category || '?') + '] ' + f.title + ' (sources: ' + ((f.sources || []).join(',')) + ')' + (f.suggestedFix ? ' -- suggested: ' + f.suggestedFix : '')).join('\n')
  return 'You are improving a SKILL.md through ONE targeted, safe edit this round. Below are findings from simulated runs plus a static audit, the list of fixes already tried this session (do NOT repeat or re-pick these), and the current SKILL.md.\n\n' +
    'Pick the SINGLE highest-leverage fix that (a) is not already tried, (b) can be made ENTIRELY within this SKILL.md text, and (c) will not break other sections. Prefer fixes that improve gating, flow, artifact completeness, internal consistency, or reduce question fatigue. Do NOT pick a fix that requires editing other files (e.g. version numbers in plugin.json / marketplace.json) - those are out of scope for this loop.\n\n' +
    'Produce minimal edits as exact string replacements. CRITICAL CONSTRAINTS on each edit: the "old" string MUST be copied VERBATIM from the SKILL.md below, MUST be short (prefer 1-4 lines), and MUST be UNIQUE in the document so it matches exactly once (include enough surrounding context to be unique, but no more). "new" is the replacement. Keep edits surgical; do not rewrite whole sections unless strictly necessary. Output the chosen fix (title, category, severity, rationale), the edits (each with a one-line why), and the expected effect on eval scores.\n\n' +
    '=== FINDINGS (highest severity first) ===\n' + (ft || '(none)') + '\n\n=== FIXES ALREADY TRIED THIS SESSION (do not repeat) ===\n' + (tried.length ? tried.join('\n') : '(none yet)') + '\n\n=== CURRENT SKILL.md ===\n' + text
}

function simThenJudge(p, text, phaseLabel) {
  // agentType:'Explore' = read-only (no Edit/Write/NotebookEdit). REQUIRED: without it the
  // default workflow subagent can edit the real SKILL.md as a side effect of "producing edits".
  return agent(simPrompt(text, p), { label: 'sim:' + p.id, phase: phaseLabel, schema: SIM_SCHEMA, model: 'sonnet', agentType: 'Explore' })
    .then((sim) => sim
      ? agent(judgePrompt(p, sim), { label: 'judge:' + p.id, phase: phaseLabel, schema: JUDGE_SCHEMA, model: 'sonnet', agentType: 'Explore' }).then((j) => (j ? { p: p.id, sim, judge: j } : null))
      : null)
}

async function evaluate(text, phaseLabel) {
  const thunks = [
    () => agent(staticPrompt(text), { label: 'static-audit', phase: phaseLabel, schema: STATIC_SCHEMA, model: 'sonnet', agentType: 'Explore' }),
    ...PERSONAS.map((p) => () => simThenJudge(p, text, phaseLabel)),
  ]
  const res = await parallel(thunks)
  const stat = res[0]
  const judged = res.slice(1).filter(Boolean)
  const score = aggregate(judged.map((x) => x.judge), stat)
  const findings = collectFindings(judged, stat)
  return { score, findings, judged, stat }
}

// ---------- main loop ----------
phase('Baseline')
log('Reading current SKILL.md...')
const readRes = await agent('Use the Read tool to read the file at ' + SKILL_PATH + ' and return its complete, exact, verbatim contents in the "content" field. Do not summarize, truncate, reformat, or alter any whitespace.', { label: 'read-skill', phase: 'Baseline', schema: READ_SCHEMA, model: 'sonnet', agentType: 'Explore' })
const startText = readRes && readRes.content ? readRes.content : ''
if (!startText || startText.length < 2000) {
  return { error: 'Could not read SKILL.md (got ' + (startText ? startText.length : 0) + ' chars). Aborting.' }
}

log('Scoring baseline (6 personas + static audit)...')
const baseEval = await evaluate(startText, 'Baseline')
let best = { text: startText, score: baseEval.score, findings: baseEval.findings, judged: baseEval.judged, label: 'baseline' }
const baselineScore = best.score
log('Baseline score: ' + round2(baselineScore) + '/5')

const tried = []
const rounds = []
const acceptedFixes = []

for (let r = 1; r <= 5; r++) {
  const ph = 'Round ' + r
  phase(ph)
  log('Round ' + r + ': diagnosing highest-leverage fix...')
  const diag = await agent(diagnosePrompt(best.findings, best.text, tried), { label: 'diagnose-r' + r, phase: ph, schema: DIAGNOSE_SCHEMA, agentType: 'Explore' })
  if (!diag || !diag.chosenFix) {
    rounds.push({ r, fix: '(diagnosis failed)', accepted: false, reason: 'no diagnosis produced', from: round2(best.score), to: null })
    continue
  }
  tried.push(diag.chosenFix.title)
  const candText = applyEdits(best.text, diag.edits)
  if (candText === null || candText === best.text) {
    rounds.push({ r, fix: diag.chosenFix.title, category: diag.chosenFix.category, severity: diag.chosenFix.severity, accepted: false, reason: 'edits did not apply uniquely / no-op', from: round2(best.score), to: null, expectedEffect: diag.expectedEffect })
    log('Round ' + r + ': edits could not be applied uniquely - skipped.')
    continue
  }
  log('Round ' + r + ': re-evaluating candidate "' + diag.chosenFix.title + '"...')
  const candEval = await evaluate(candText, ph)
  const accepted = candEval.score >= best.score
  rounds.push({ r, fix: diag.chosenFix.title, category: diag.chosenFix.category, severity: diag.chosenFix.severity, from: round2(best.score), to: round2(candEval.score), accepted, expectedEffect: diag.expectedEffect, rationale: diag.chosenFix.rationale })
  if (accepted) {
    best = { text: candText, score: candEval.score, findings: candEval.findings, judged: candEval.judged, label: 'r' + r }
    acceptedFixes.push({ title: diag.chosenFix.title, category: diag.chosenFix.category, severity: diag.chosenFix.severity, rationale: diag.chosenFix.rationale, edits: diag.edits })
    log('Round ' + r + ': ACCEPTED (' + round2(candEval.score) + ' >= ' + round2(best.score === candEval.score ? baselineScore : best.score) + ').')
  } else {
    log('Round ' + r + ': REJECTED (' + round2(candEval.score) + ' < ' + round2(best.score) + ') - keeping previous best, will try a different fix next round.')
  }
}

return {
  baselineScore: round2(baselineScore),
  finalScore: round2(best.score),
  improvement: round2(best.score - baselineScore),
  acceptedCount: acceptedFixes.length,
  rounds,
  acceptedFixes,
  topRemainingFindings: best.findings.slice(0, 10).map((f) => ({ title: f.title, severity: f.severity, category: f.category, sources: f.sources, suggestedFix: f.suggestedFix })),
  perPersonaFinal: best.judged.map((x) => ({ persona: x.p, overall: x.judge.overall, lens: x.judge.lensScores, failedContract: x.judge.contractChecks.filter((c) => !c.passed).map((c) => c.behavior) })),
}
