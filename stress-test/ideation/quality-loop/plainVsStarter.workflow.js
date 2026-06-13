export const meta = {
  name: 'ideation-plain-vs-starter',
  description: 'The GATE for the lean-default move: does ONE plain brainstorm call (no frame/personas/techniques) lose idea quality vs the current starter default (frame + 2 personas)? Blind substance A/B (relevance held) + distinct-mechanism census. Same N=16/condition, both arms use the real mechanism-first output-rules so the only variable is the generation machinery.',
  phases: [
    { title: 'Generate', detail: 'plain one-call vs starter (frame + 2 personas)' },
    { title: 'Measure', detail: 'blind substance A/B + distinct-mechanism census' },
  ],
}

const ROOT = '/Users/ydmitry/work/logbook-creator'
const SK = `${ROOT}/plugins/ideation/skills/ideation`
const PD = `${ROOT}/stress-test/ideation/quality-loop/track-c/prompts-base` // real baseline generate.seed + personas
const OUTRULES = `${SK}/references/output-rules.md`                          // real, mechanism-first (shared by both arms)

const FRAMES = {
  'cafe-afternoon-revenue': {
    problem: "A neighbourhood cafe is packed 7-11am but nearly empty 2-5pm; the owner wants to grow afternoon revenue without cannibalising the morning rush.",
    rc: ["No commuter foot traffic after lunch.", "Known as a morning coffee stop, not an afternoon destination.", "Staff and ovens sit idle in the afternoon but still cost money.", "Regulars have no habit or trigger to return later."],
    hmw: ["Give morning customers a reason to return in the afternoon", "Turn idle afternoon capacity into a sellable product", "Attract a different afternoon crowd without alienating regulars", "Make the slow hours feel like a feature"],
    triz: "Filling the afternoon risks straining the morning brand/quality.",
  },
  'b2b-saas-early-churn': {
    problem: "A small B2B SaaS team-scheduling tool (~400 paying teams) loses ~4% of accounts/month, mostly in the first 60 days; the founder wants to cut early churn.",
    rc: ["Teams never reach the 'aha' (a first fully-scheduled week) before novelty fades.", "Only the admin logs in; the team never adopts.", "Time-saved value is invisible.", "Switching cost is low early; a competitor is one CSV export away."],
    hmw: ["Get a whole team active in week one, not just the admin", "Make the time-saved value visible early", "Raise the cost of leaving without locking people in", "Detect a team about to churn and intervene"],
    triz: "Pushing adoption nudges harder risks accelerating the churn you're preventing.",
  },
}
const TOPICS = ['cafe-afternoon-revenue', 'b2b-saas-early-churn']
const avg = (xs) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0
const r1 = (x) => Math.round(x * 100) / 100
const frameText = (t) => { const f = FRAMES[t]; return `Problem: ${f.problem}\nRoot causes:\n- ${f.rc.join('\n- ')}\nHMW directions:\n- ${f.hmw.join('\n- ')}\nKey trade-off: ${f.triz}` }

const IDEAS_CELL = { type: 'object', additionalProperties: false, required: ['ideas'], properties: { ideas: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['title', 'description', 'tag'], properties: { title: { type: 'string' }, description: { type: 'string' }, tag: { type: 'string', enum: ['SAFE', 'BOLD', 'WILD'] } } } } } }
const AXES = { type: 'object', additionalProperties: false, required: ['novelty', 'mechanism', 'relevance', 'compliance'], properties: { novelty: { type: 'number' }, mechanism: { type: 'number' }, relevance: { type: 'number' }, compliance: { type: 'number' } } }
const ABJUDGE = { type: 'object', additionalProperties: false, required: ['scores_X', 'scores_Y', 'better_substance', 'reason'], properties: { scores_X: AXES, scores_Y: AXES, better_substance: { type: 'string', enum: ['X', 'Y', 'tie'] }, reason: { type: 'string' } } }
const CENSUS = { type: 'object', additionalProperties: false, required: ['set1', 'set2', 'note'], properties: {
  set1: { type: 'object', additionalProperties: false, required: ['distinct_all16'], properties: { distinct_all16: { type: 'number' } } },
  set2: { type: 'object', additionalProperties: false, required: ['distinct_all16'], properties: { distinct_all16: { type: 'number' } } },
  note: { type: 'string' } } }

const plainPrompt = (topic) => `You are brainstorming ideas for a real problem. FIRST read ${OUTRULES} and follow its description discipline (mechanism-first, coffee-talk, concrete, self-contained) for every idea. Then brainstorm BROADLY and produce exactly 16 varied, concrete ideas — each a title + a 2-3 sentence description. Do NOT use any formal technique, framework, persona, or framing exercise; just brainstorm well in one pass. Vary SAFE/BOLD/WILD across the set. Return via schema. Do not narrate.

Problem: ${FRAMES[topic].problem}`

const starterPrompt = (topic, persona) => `You are the \`generate.seed\` operator of the ideation skill. Read these files NOW and follow them VERBATIM:
- ${PD}/generate.seed.md
- ${OUTRULES}
- ${PD}/${persona}.md

Active frame:
${frameText(topic)}

Produce exactly 8 raw seed ideas in the "${persona}" voice for this frame, honoring every instruction. Return via schema. Do not narrate.`

const renderSet = (ideas) => ideas.map((i, k) => `${k + 1}. [${i.tag}] ${i.title} — ${i.description}`).join('\n')

const abPrompt = (topic, xSet, ySet) => `Impartial idea-quality judge. Two anonymous collections of 16 brainstorm ideas for the SAME problem — Collection X and Collection Y. You know nothing about how either was produced.

Problem: ${FRAMES[topic].problem}

Score EACH collection 1-5 on FOUR separate axes (do not blend):
- novelty: non-obviousness (first answers anyone reaches for score low)
- mechanism: concrete who-does-what specificity (vague slogan scores low)
- relevance: actually attacks THIS problem / its root causes (clever-but-off-topic scores low)
- compliance: self-contained coffee-talk, concrete example, no jargon
Weigh coverage and within-collection repetition (same idea twice = novelty failure).

Then say which has higher SUBSTANCE (novelty+mechanism+relevance) — X, Y, or tie — in 3-4 sentences, noting if either bought novelty at the cost of relevance.

COLLECTION X:
${xSet}

COLLECTION Y:
${ySet}`

const censusPrompt = (topic, c1, c2) => `Mechanism diversity audit. Two collections (1, 2) of 16 ideas each for the same problem. Use ONE shared mechanism vocabulary across BOTH; strip prose to the core move; label every idea; granularity identical across collections. For each collection report distinct_all16 = number of DISTINCT mechanism labels across its 16 ideas (overall variety). Problem: ${FRAMES[topic].problem}

COLLECTION 1:
${c1}

COLLECTION 2:
${c2}`

// ---- generate ----
phase('Generate')
const cells = []
for (const topic of TOPICS) {
  cells.push({ kind: 'plain', topic })
  cells.push({ kind: 'starter', topic, persona: 'innovator' })
  cells.push({ kind: 'starter', topic, persona: 'wild_card' })
}
const gens = await parallel(cells.map(c => () => {
  const p = c.kind === 'plain' ? plainPrompt(c.topic) : starterPrompt(c.topic, c.persona)
  return agent(p, { schema: IDEAS_CELL, label: `${c.kind}${c.persona ? ':' + c.persona : ''}@${c.topic.slice(0, 8)}`, phase: 'Generate', agentType: 'general-purpose' })
    .then(o => ({ ...c, ideas: o && o.ideas ? o.ideas : [] })).catch(() => ({ ...c, ideas: [] }))
}))
const plainIdeas = (topic) => (gens.find(g => g.kind === 'plain' && g.topic === topic) || {}).ideas || []
const starterIdeas = (topic) => {
  const inn = (gens.find(g => g.kind === 'starter' && g.topic === topic && g.persona === 'innovator') || {}).ideas || []
  const wld = (gens.find(g => g.kind === 'starter' && g.topic === topic && g.persona === 'wild_card') || {}).ideas || []
  return [...inn, ...wld]
}

// ---- measure ----
phase('Measure')
const perTopic = []
for (const topic of TOPICS) {
  const plainSet = renderSet(plainIdeas(topic))
  const starterSet = renderSet(starterIdeas(topic))
  // blind, position-swapped: j1 X=plain Y=starter ; j2 X=starter Y=plain
  const [j1, j2, cen] = await parallel([
    () => agent(abPrompt(topic, plainSet, starterSet), { schema: ABJUDGE, label: `ab ${topic.slice(0, 8)} X=plain`, phase: 'Measure' }).catch(() => null),
    () => agent(abPrompt(topic, starterSet, plainSet), { schema: ABJUDGE, label: `ab ${topic.slice(0, 8)} X=starter`, phase: 'Measure' }).catch(() => null),
    () => agent(censusPrompt(topic, plainSet, starterSet), { schema: CENSUS, label: `census ${topic.slice(0, 8)}`, phase: 'Measure' }).catch(() => null),
  ])
  const plainScores = [j1 && j1.scores_X, j2 && j2.scores_Y].filter(Boolean)
  const starterScores = [j1 && j1.scores_Y, j2 && j2.scores_X].filter(Boolean)
  const aa = (arr, k) => r1(avg(arr.map(s => s[k])))
  const prefers = [
    j1 ? (j1.better_substance === 'X' ? 'plain' : j1.better_substance === 'Y' ? 'starter' : 'tie') : null,
    j2 ? (j2.better_substance === 'Y' ? 'plain' : j2.better_substance === 'X' ? 'starter' : 'tie') : null,
  ].filter(Boolean)
  perTopic.push({
    topic,
    plain: { novelty: aa(plainScores, 'novelty'), mechanism: aa(plainScores, 'mechanism'), relevance: aa(plainScores, 'relevance'), compliance: aa(plainScores, 'compliance'), count: plainIdeas(topic).length },
    starter: { novelty: aa(starterScores, 'novelty'), mechanism: aa(starterScores, 'mechanism'), relevance: aa(starterScores, 'relevance'), compliance: aa(starterScores, 'compliance'), count: starterIdeas(topic).length },
    prefers,
    reasons: [j1 && j1.reason, j2 && j2.reason].filter(Boolean),
    distinct: cen ? { plain: cen.set1.distinct_all16, starter: cen.set2.distinct_all16, note: cen.note } : null,
  })
  log(`${topic}: prefers=${prefers.join(',')} | distinct plain/starter=${cen && cen.set1.distinct_all16}/${cen && cen.set2.distinct_all16}`)
}

const overall = (cond, k) => r1(avg(perTopic.map(t => t[cond][k])))
const subst = (cond) => r1(avg(['novelty', 'mechanism', 'relevance'].map(k => overall(cond, k))))
return {
  verdict_note: 'GATE for lean default. Green light = plain TIES or BEATS starter on blind substance with relevance not down. n=2 frames; only a LARGE delta is interpretable (substance bounces ~0.3 in noise). distinct_all16 shows whether one plain call is more/less diverse than 2 personas.',
  substance: { plain: subst('plain'), starter: subst('starter') },
  axes: { plain: { novelty: overall('plain', 'novelty'), mechanism: overall('plain', 'mechanism'), relevance: overall('plain', 'relevance'), compliance: overall('plain', 'compliance') }, starter: { novelty: overall('starter', 'novelty'), mechanism: overall('starter', 'mechanism'), relevance: overall('starter', 'relevance'), compliance: overall('starter', 'compliance') } },
  distinct_all16: { plain: r1(avg(perTopic.map(t => t.distinct ? t.distinct.plain : 0))), starter: r1(avg(perTopic.map(t => t.distinct ? t.distinct.starter : 0))) },
  prefers_overall: perTopic.flatMap(t => t.prefers),
  per_topic: perTopic,
}
