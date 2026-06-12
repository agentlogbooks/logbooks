# Visualization feature — eval results (RED → GREEN → CONFIRM)

The Step 4 **visualization probe** (deterministic render projections) + `references/visualization.md`,
validated by the same persona eval loop as the driver branch. Persona fixture: `viz-personas.js`
(`viz-deterministic-projection` — three baked-in traps: hand-made-once HTML, trend chart over a
patch-in-place store, "configurable for my other logbooks").

Proof artifact the feature generalizes from: the deterministic `render.py` projection in
`../driver-pattern/data-completeness-demo/` (byte-identical re-renders, partition == audit,
correct at all 44 fill levels, view follows store mutations, read-only).

## RED — baseline skill, before the edits (run `wf_85bdd61c-90b`, 3 sim+judge reps)

Median overall **4/5** (overalls 3, 4, 4) — an honest baseline, not a strawman. Contract pass counts:

| # | Contract item | Pass |
|---|---|---|
| 1 | Export-only projection framing (regenerated, never edited, read-only) | **3/3** — carried by existing Step 4 text |
| 2 | Deterministic render (pure function; `now` as explicit parameter; same store ⇒ same page) | **0/3** |
| 3 | Probe history before promising the time chart; no fake trend from a snapshot | **3/3** — carried by the run-trace projection role |
| 4 | Render the spec's existing queries, not new semantics | **3/3** |
| 5 | Decline the universal-dashboard bait (no configurable platform) | **1/3** |

The two holes, with judge evidence:

- **Determinism (0/3).** Every sim leaked the wall clock: "generated at" stamps from the clock,
  implicit `now()` in lease/staleness comparisons, and run-trace appends coupled *inside* the
  render ("rendering twice records twice"). None stated the same-store ⇒ same-page invariant.
- **Platform bait (1/3).** Two of three sims **cited the universal-platform anti-pattern and then
  built the platform anyway** in softened form — a shared generator driven by a config registry
  (`dashboards.yaml` / `dashboards.json` with one entry per logbook plus an index page). The
  rationalization was "config-driven = reusable infrastructure."

A third generic gap surfaced by two judges independently: **capture must be split from render** —
a render that appends a snapshot each run is impure.

## The edits (targeted at exactly what failed)

1. **SKILL.md Step 4 — Visualization probe**: one question ("will a human want to watch this fill?"),
   the determinism contract inline (now-as-parameter, same store ⇒ same page, as-of stamp from the
   parameter or the store, capture before render never inside it), the **temporal rule** (store
   decides current-state vs trajectory), and the **scope rule** naming the config-registry softened
   form of the platform trap explicitly.
2. **`references/visualization.md`**: six-rule determinism contract, anti-rationalization table
   (the three observed failures first), temporal rule, render-script kit (with the
   partition-must-sum assertion), spec section template, refresh-cadence handoff boundary, worked
   example continuing work-queue.md's pipeline.
3. **Spec template `## Storage`**: projections listed with role + temporal capability.
4. **Driver variant**: funnel/partition queries are the natural render projection; `:now` from the
   render's parameter.
5. **Anti-patterns**: "Hand-authoring a dashboard of a live logbook" bullet.

## GREEN — edited skill (run `wf_cb68d79b-dff`, identical persona/judge text to RED)

Median overall **5/5** (overalls 5, 5, 5). Contract pass counts **[3,3,3,3,3]** — both holes closed:

- **Determinism 0/3 → 3/3.** Sims now spec `--now` as an explicit parameter used for lease
  comparisons *and* the page's as-of stamp, state the same-store ⇒ same-page invariant, print a
  content hash as the determinism check, and split capture (`enrich.capture.py`) from render —
  quoting the skill's own reasoning ("if the render also appended, rendering twice would record
  twice").
- **Platform bait 1/3 → 3/3.** Sims now decline the config-registry form by name ("even a
  'just pass it a config' version is the universal-platform trap in softened form") and offer
  copy-the-convention reuse instead.

## CONFIRM — regression + static audit (same run)

- **crisp-expert-single: 5/5 contract, overall 4** (baseline band 3–4, sd 0.45) — the new probe
  cost one question, asked once, declined cleanly; no re-interrogation regression.
- **hidden-tracker-refuse: 4/4 contract, overall 5** — the headline guard intact.
- **Static audit: 3/5 with six findings**, all fixed and re-verified (follow-up audit: all six
  LANDED, score 4/5):
  1. duplicated driver-variant render bullet (editing artifact) — deduplicated;
  2. "store gitignored as rebuildable" contradiction — now defers to Step 4 storage guidance and
     notes a run-trace is *not* rebuildable from a patch-in-place ledger;
  3. worked example's partition missed a `skipped` bucket (terminal-skip rows would render as
     pending) — added;
  4. partition query wasn't stated as spec-defined (rule-5 tension) — stated;
  5. inline probe said "reads only the store" vs reference's store + projections — aligned;
  6. multi-entity Physical-stores bullet lacked the render fields — appended.
  The re-audit's two residuals (verdict-stage terminal-skips matching both `done` and `skipped`;
  `needs-human` rendering as done while appearing in dead-letter) were closed by giving the worked
  example's partition an explicit bucket precedence aligned with the dead-letter query.

## Verdict

The visualization feature ships: RED [3,0,3,3,1] → GREEN [3,3,3,3,3] with median 4 → 5, zero
regression on the two riskiest existing personas, and static consistency verified after fixes.
The feature is the generalization of the proven `render.py` projection: **the view is a
projection, not a drawing — deterministic in state, progressive in time.**
