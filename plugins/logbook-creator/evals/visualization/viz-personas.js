// Visualization eval persona — hidden-state stress test for the Step 4 visualization probe
// (deterministic render projections). Same { id, brief, contract, groundTruth } shape as
// ../driver-pattern/driver-personas.js, so it drops straight into the self-improve.workflow.js harness.
//
// The three traps it bakes in are the generic failure modes of any "visualize my logbook" ask:
//   1. hand-made-once HTML (drift / second source of truth),
//   2. a progress-over-time chart promised over a patch-in-place store (no history retained),
//   3. "make it configurable for my other logbooks" (the universal-dashboard platform bait).
//
// RED baseline (2026-06-12, run wf_85bdd61c-90b: 3 sim+judge reps against the pre-visualization
// skill): median overall 4/5; contract pass counts [3,0,3,3,1] of 3 — items 1/3/4 already carried
// by the existing Step 4 projection text; item 2 (deterministic render: now-as-parameter, same
// store => same page, capture split from render) 0/3; item 5 (decline the platform bait) 1/3,
// with two sims building a config-registry generator WHILE citing the universal-platform
// anti-pattern. See RESULTS.md. Goes green only with the Step 4 visualization probe +
// references/visualization.md.

const VIZ_GROUND_TRUTH = [
  'Correct handling of "visualize my logbook" looks like this:',
  '- The visualization is an EXPORT-ONLY PROJECTION: view = render(store). A pure, read-only function',
  '  of the authoritative store. Regenerated wholesale on each run; never edited by hand; never a',
  '  second source of truth. A render that WRITES to the store is a mirror (anti-pattern).',
  '- DETERMINISTIC: no wall clock (time enters only as an explicit query parameter), no randomness,',
  '  no network fetches, no numbers typed by a human into the page. Same store bytes => same page.',
  '  Any as-of stamp on the page comes from the explicit now-parameter or the store itself.',
  '- A one-off hand-authored HTML page is the failure mode: stale after the next write, numbers drift',
  '  from the store. The deliverable is a RENDER SCRIPT to re-run, not a page.',
  '- If a run-trace snapshot is captured, capture is a SEPARATE step before the render, never inside',
  '  it - a render that appends a snapshot each run makes rendering twice differ from rendering once.',
  '- TEMPORAL CAPABILITY belongs to the store, not the renderer: a patch-in-place ledger can only',
  '  render CURRENT STATE; a trajectory/burndown chart requires retained history (append-only',
  '  run-trace or transition timestamps). Promising a time chart without checking this is an error.',
  '- The renderer visualizes the queries the logbook spec already defines (funnel/partition,',
  '  dead-letter, validation), not new semantics invented in the view layer.',
  '- "Make it configurable for all my logbooks" is the universal-platform trap: one logbook, one',
  '  render script bound to that logbook\'s spec. A shared generator driven by a config registry is',
  '  the same trap in softened form. Reuse via copying the convention, not a platform.',
].join('\n')

const VIZ_PERSONAS = [
  {
    id: 'viz-deterministic-projection',
    groundTruth: VIZ_GROUND_TRUTH,
    brief:
      'You are a growth engineer. You ALREADY HAVE a working logbook (do not redesign it): a SQLite ' +
      'company-enrichment queue at ~/state/enrich/enrich.db that several worker agents fill across ' +
      'sessions (per-stage status columns, attempts counters, lease columns - designed properly ' +
      'earlier). What you want NOW: "a dashboard so I can actually SEE what is happening - where ' +
      'every company stands, and a chart of progress over time. Can you make me an HTML page for ' +
      'that?" Workers re-run daily, so the picture changes every day. HIDDEN FACT 1 (reveal ONLY if ' +
      'asked whether the store retains history / transition timestamps / how past states would be ' +
      'known): the ledger is patch-in-place - statuses are overwritten in the same row; nothing ' +
      'records WHEN a transition happened. You are not aware this matters for a time chart. HIDDEN ' +
      'FACT 2 (reveal ONLY if asked how the page should be produced, refreshed, or kept current): ' +
      'you assumed someone just makes the HTML once; you had not thought about it going stale after ' +
      'tomorrow\'s runs. MID-CONVERSATION (once a basic view is being discussed, raise this ' +
      'yourself, verbatim): "actually, can you make it configurable so I can point it at my other ' +
      'two logbooks as well?" You are agreeable and accept good guidance, but you NEVER volunteer ' +
      'the hidden facts unprompted, and you happily accept a one-off hand-made HTML page if that is ' +
      'what is offered.',
    contract: [
      'Frames the visualization as an export-only PROJECTION of the authoritative store: regenerated wholesale from the store, never hand-edited, never a second source of truth, and read-only on the store',
      'Specs a DETERMINISTIC render script - a pure function of the store: no wall clock (any "now" is an explicit parameter), no randomness, no network, no hand-typed numbers; re-running on the same store yields the same page; output is self-contained HTML',
      'Probes whether the store retains history BEFORE promising the progress-over-time chart; on learning the ledger is patch-in-place, does NOT fake a trend from a snapshot - offers current-state now and an append-only run-trace (or transition timestamps) to enable trajectory going forward',
      'The view renders the queries the logbook spec already defines (funnel/partition, ready, dead-letter, validation) rather than inventing new semantics in the renderer',
      'Declines the universal-dashboard bait: keeps the render script bound to THIS logbook\'s spec, offering reuse via convention/template rather than building one configurable dashboard platform for all logbooks',
    ],
  },
]

if (typeof module !== 'undefined') module.exports = { VIZ_PERSONAS, VIZ_GROUND_TRUTH }
