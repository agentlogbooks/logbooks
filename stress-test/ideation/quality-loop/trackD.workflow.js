export const meta = {
  name: 'ideation-trackD-input-diversification',
  description: 'Track D: idea quality via INPUT diversification (each persona gets a disjoint slice of the frame) vs baseline. Blind substance A/B (relevance held) is the verdict; census reports OVERALL distinct mechanisms across all 16 (real diagnostic) + cross-persona collisions (manipulation check).',
  phases: [
    { title: 'Generate', detail: 'baseline (full frame) vs fix (disjoint slices per persona)' },
    { title: 'Measure', detail: 'blind substance A/B + overall-distinct census' },
  ],
}

const ROOT = '/Users/ydmitry/work/logbook-creator'
const PD = `${ROOT}/stress-test/ideation/quality-loop/track-c/prompts-base` // real baseline prompts (unchanged)

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
// disjoint slices per persona (input diversification): indices into rc/hmw
const SLICES = {
  'cafe-afternoon-revenue': { innovator: { rc: [2, 3], hmw: [1, 3] }, wild_card: { rc: [0, 1], hmw: [0, 2] } },
  'b2b-saas-early-churn': { innovator: { rc: [0, 2], hmw: [0, 1] }, wild_card: { rc: [1, 3], hmw: [2, 3] } },
}
const TOPICS = ['cafe-afternoon-revenue', 'b2b-saas-early-churn']
const PERSONAS = ['innovator', 'wild_card']
const N = 8
const avg = (xs) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0
const r1 = (x) => Math.round(x * 100) / 100

function frameText(topic, slice) {
  const f = FRAMES[topic]
  const rc = slice ? slice.rc.map(i => f.rc[i]) : f.rc
  const hmw = slice ? slice.hmw.map(i => f.hmw[i]) : f.hmw
  return `Problem: ${f.problem}\nRoot causes to attack:\n- ${rc.join('\n- ')}\nHMW directions:\n- ${hmw.join('\n- ')}\nKey trade-off: ${f.triz}`
}

const IDEAS_CELL = { type: 'object', additionalProperties: false, required: ['ideas'], properties: { ideas: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['title', 'description', 'tag'], properties: { title: { type: 'string' }, description: { type: 'string' }, tag: { type: 'string', enum: ['SAFE', 'BOLD', 'WILD'] } } } } } }
const AXES = { type: 'object', additionalProperties: false, required: ['novelty', 'mechanism', 'relevance', 'compliance'], properties: { novelty: { type: 'number' }, mechanism: { type: 'number' }, relevance: { type: 'number' }, compliance: { type: 'number' } } }
const ABJUDGE = { type: 'object', additionalProperties: false, required: ['scores_X', 'scores_Y', 'better_substance', 'reason'], properties: { scores_X: AXES, scores_Y: AXES, better_substance: { type: 'string', enum: ['X', 'Y', 'tie'] }, reason: { type: 'string' } } }
const CENSUS = { type: 'object', additionalProperties: false, required: ['set1', 'set2', 'note'], properties: {
  set1: { type: 'object', additionalProperties: false, required: ['distinct_all16', 'cross_maker_collisions'], properties: { distinct_all16: { type: 'number' }, cross_maker_collisions: { type: 'number' } } },
  set2: { type: 'object', additionalProperties: false, required: ['distinct_all16', 'cross_maker_collisions'], properties: { distinct_all16: { type: 'number' }, cross_maker_collisions: { type: 'number' } } },
  note: { type: 'string' } } }

const genPrompt = (topic, persona, slice) => `You are the \`generate.seed\` operator of the ideation skill. Read these files NOW and follow them VERBATIM — they define your procedure, output discipline, and persona voice:
- ${PD}/generate.seed.md
- ${PD}/output-rules.md
- ${PD}/${persona}.md

Active frame for this batch:
${frameText(topic, slice)}

Produce exactly ${N} raw seed ideas in the "${persona}" voice for this frame, honoring every instruction in those files. Return via schema. Do not narrate.`

const renderSet = (innovator, wild) => `Maker A:\n${(innovator || []).map((i, k) => `${k + 1}. [${i.tag}] ${i.title} — ${i.description}`).join('\n')}\n\nMaker B:\n${(wild || []).map((i, k) => `${k + 1}. [${i.tag}] ${i.title} — ${i.description}`).join('\n')}`

const abPrompt = (topic, xSet, ySet) => `You are an impartial idea-quality judge. Two anonymous collections of brainstorm ideas for the SAME problem are below — Collection X and Collection Y. Each has 16 ideas from two makers (A, B). You know nothing about how either was produced.

Problem: ${FRAMES[topic].problem}

Score EACH collection 1-5 (3=average, 5=rare) on FOUR separate axes — do not blend:
- novelty: non-obviousness (the first answers anyone reaches for score low)
- mechanism: concrete who-does-what specificity (vague direction/slogan scores low)
- relevance: does it actually attack THIS stated problem / its root causes (a clever idea that doesn't move this problem scores LOW even if novel)
- compliance: self-contained coffee-talk, concrete example, no jargon/methodology/timeline
Weigh overall coverage of the problem and within-collection repetition (the same idea twice is a novelty failure).

Then say which collection has higher SUBSTANCE (novelty+mechanism+relevance) — X, Y, or tie — in 3-4 sentences, explicitly noting if either bought novelty at the cost of relevance, OR achieved variety only by scattering across unrelated micro-topics.

COLLECTION X:
${xSet}

COLLECTION Y:
${ySet}`

const censusPrompt = (topic, c1, c2) => `Mechanism diversity audit. Two collections (Collection 1, Collection 2) of 16 ideas each for the same problem; each has two makers (A, B).

Problem: ${FRAMES[topic].problem}

Use ONE shared mechanism vocabulary across BOTH collections. Read all 32 ideas, settle on consistent short mechanism labels (2-4 words, e.g. "rent idle capacity", "raise switching cost", "make value visible"), strip evocative prose to the core move, then label every idea. Granularity MUST be identical across both collections.

For EACH collection report:
- distinct_all16: how many DISTINCT mechanism labels appear across ALL 16 of its ideas (this is the primary number — overall variety)
- cross_maker_collisions: how many labels appear in BOTH maker A and maker B
IMPORTANT: a collection can have FEW cross-maker collisions yet LOW distinct_all16 if each maker repeats the same mechanism within its own 8 (convergence relocated, not removed). Report distinct_all16 honestly — do not split mechanisms more finely in one collection than the other.

COLLECTION 1:
${c1}

COLLECTION 2:
${c2}`

// ---- generate ----
phase('Generate')
const jobs = []
for (const topic of TOPICS) for (const persona of PERSONAS) {
  jobs.push({ cond: 'base', topic, persona, slice: null })
  jobs.push({ cond: 'fix', topic, persona, slice: SLICES[topic][persona] })
}
const gens = await parallel(jobs.map(j => () =>
  agent(genPrompt(j.topic, j.persona, j.slice), { schema: IDEAS_CELL, label: `gen ${j.cond} ${j.persona}@${j.topic.slice(0, 8)}`, phase: 'Generate', agentType: 'general-purpose' })
    .then(o => ({ ...j, ideas: o && o.ideas ? o.ideas : [] })).catch(() => ({ ...j, ideas: [] }))))
const get = (cond, topic, persona) => (gens.find(g => g.cond === cond && g.topic === topic && g.persona === persona) || {}).ideas || []

// ---- measure ----
phase('Measure')
const perTopic = []
for (const topic of TOPICS) {
  const baseSet = renderSet(get('base', topic, 'innovator'), get('base', topic, 'wild_card'))
  const fixSet = renderSet(get('fix', topic, 'innovator'), get('fix', topic, 'wild_card'))
  const [j1, j2, cen] = await parallel([
    () => agent(abPrompt(topic, baseSet, fixSet), { schema: ABJUDGE, label: `ab ${topic.slice(0, 8)} X=base`, phase: 'Measure' }).catch(() => null),
    () => agent(abPrompt(topic, fixSet, baseSet), { schema: ABJUDGE, label: `ab ${topic.slice(0, 8)} X=fix`, phase: 'Measure' }).catch(() => null),
    () => agent(censusPrompt(topic, baseSet, fixSet), { schema: CENSUS, label: `census ${topic.slice(0, 8)}`, phase: 'Measure' }).catch(() => null),
  ])
  const baseScores = [j1 && j1.scores_X, j2 && j2.scores_Y].filter(Boolean)
  const fixScores = [j1 && j1.scores_Y, j2 && j2.scores_X].filter(Boolean)
  const aa = (arr, k) => r1(avg(arr.map(s => s[k])))
  const prefers = [
    j1 ? (j1.better_substance === 'Y' ? 'fix' : j1.better_substance === 'X' ? 'base' : 'tie') : null,
    j2 ? (j2.better_substance === 'X' ? 'fix' : j2.better_substance === 'Y' ? 'base' : 'tie') : null,
  ].filter(Boolean)
  perTopic.push({
    topic,
    base: { novelty: aa(baseScores, 'novelty'), mechanism: aa(baseScores, 'mechanism'), relevance: aa(baseScores, 'relevance'), compliance: aa(baseScores, 'compliance') },
    fix: { novelty: aa(fixScores, 'novelty'), mechanism: aa(fixScores, 'mechanism'), relevance: aa(fixScores, 'relevance'), compliance: aa(fixScores, 'compliance') },
    prefers,
    reasons: [j1 && j1.reason, j2 && j2.reason].filter(Boolean),
    census: cen ? { base: cen.set1, fix: cen.set2, note: cen.note } : null,
  })
  log(`${topic}: base distinct16=${cen && cen.set1.distinct_all16} fix distinct16=${cen && cen.set2.distinct_all16} | prefers=${prefers.join(',')}`)
}

const overall = (cond, k) => r1(avg(perTopic.map(t => t[cond][k])))
const subst = (cond) => r1(avg(['novelty', 'mechanism', 'relevance'].map(k => overall(cond, k))))
return {
  verdict_note: 'Verdict = blind substance A/B with relevance flat-or-up. Census distinct_all16 is the real diversity diagnostic (overall variety); cross_maker_collisions is only a manipulation check (partitioning inputs drops it near-tautologically). Watch for "collisions down, distinct_all16 flat, substance flat" = lever engaged, didn\'t help. n=2 frames.',
  substance: { base: subst('base'), fix: subst('fix') },
  axes: { base: { novelty: overall('base', 'novelty'), mechanism: overall('base', 'mechanism'), relevance: overall('base', 'relevance'), compliance: overall('base', 'compliance') }, fix: { novelty: overall('fix', 'novelty'), mechanism: overall('fix', 'mechanism'), relevance: overall('fix', 'relevance'), compliance: overall('fix', 'compliance') } },
  census_distinct_all16: { base: r1(avg(perTopic.map(t => t.census ? t.census.base.distinct_all16 : 0))), fix: r1(avg(perTopic.map(t => t.census ? t.census.fix.distinct_all16 : 0))) },
  prefers_overall: perTopic.flatMap(t => t.prefers),
  per_topic: perTopic,
}
