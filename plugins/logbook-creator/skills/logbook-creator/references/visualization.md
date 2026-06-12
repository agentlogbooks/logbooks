# Visualizing a logbook (deterministic render projections)

Internal documentation for the Step 4 visualization probe. A logbook visualization is an
**export-only projection that renders to a file**: `view = render(store)` — a pure, read-only
function of the authoritative store. The page is not drawn; it is the store, rendered. Re-run the
script after writes and the view tracks progress: **deterministic in state, progressive in time.**

This file is generic. The contract and templates use placeholders; one compact worked example at
the end (continuing `work-queue.md`'s literature-review pipeline) makes them concrete.

## When it applies

The probe fires in Step 4 (Projections) when a human wants to *watch* the logbook — a dashboard,
a progress view, "where does everything stand?". The deliverable is a **render script**, never a
page: a one-off hand-authored page is stale after the next write and its numbers drift from the
store, which is the "hand-maintained second source of truth" anti-pattern in the view layer.

The render projection is orthogonal to single-table vs. multi-entity and to the driver dimension —
any logbook can have one. For **driver logbooks** it is the natural payoff: the funnel/partition
queries the driver spec already defines *are* the dashboard (completeness becomes visible, not just
queryable).

## The determinism contract (six rules)

1. **Pure function of the store.** The only inputs are the authoritative store, its projections
   (e.g. a run-trace), and static configuration fixed in the script. No network fetches, no
   environment lookups, no hand-typed numbers. Same store bytes ⇒ byte-identical view.
2. **Time is a parameter, not a clock.** If any query needs "now" (lease expiry, staleness), the
   script takes it as an explicit argument with a documented default — never the wall clock. Any
   as-of stamp shown on the page comes from that parameter or from the store's own timestamps,
   never from the clock. This is what makes a render reproducible and testable.
3. **Read-only on the store — and capture is not render.** The render opens the store read-only
   and writes only its output file. A render that claims, advances, or annotates rows is a
   **mirror** — it corrupts the source of truth. And if a run-trace snapshot is captured, that is
   a separate *capture* step that runs before the render, never inside it: a render that records a
   snapshot each time it runs makes rendering twice differ from rendering once.
4. **Regenerate, never edit.** The output is overwritten wholesale each run and carries a
   `GENERATED — do not edit` header naming the script. Hand-editing the output recreates the
   second-source-of-truth anti-pattern.
5. **Render the spec's queries, not new semantics.** The view visualizes the queries the logbook
   spec already defines — funnel/partition, validation, dead-letter, summary stats. If the view
   needs a number the spec has no query for, add the query to the spec first; the renderer invents
   nothing.
6. **Self-contained output.** One file (HTML with inline CSS/JS, SVG, or markdown), openable
   anywhere with no server, CDN, or build step. The view must outlive the machine that rendered it.

## Anti-rationalization table

Each shortcut feels reasonable in the moment and is wrong (the first three are the ones observed
failing in baseline evals):

| If you catch yourself thinking… | Stop — the rule is |
|---|---|
| "The page needs a 'generated at' banner so staleness is visible." | Stamp the page with the explicit `--now` parameter or the store's own latest timestamp — never the wall clock, or no two renders agree. *(Rule 2)* |
| "The refresh script can append today's snapshot and then render." | Capture and render are separate steps. A render that also appends makes rendering twice record twice. *(Rule 3)* |
| "A shared generator with a config registry isn't a universal dashboard — it's reusable infrastructure." | A config-registry-driven generic renderer *is* the universal-platform trap in softened form. One logbook, one render script bound to that spec; reuse by copying the convention to the next logbook's own script and spec. |
| "I'll just make them a nice HTML page with the current numbers." | A hand-authored page drifts on the next write. Deliver a **render script** that regenerates the page from the store. *(Rules 1, 4)* |
| "They'll want a progress-over-time chart — I'll chart the snapshot." | A single snapshot has no history. A trajectory requires retained history; see the temporal rule below. |
| "While rendering I can also mark the rows I displayed." | A render that writes to the store is a mirror, not a projection. Read-only, always. *(Rule 3)* |
| "The dashboard needs a metric the spec doesn't define — I'll compute it in the renderer." | Then the spec is incomplete. Add the query to the spec first; the renderer only renders. *(Rule 5)* |

## The temporal rule — the store decides what the view can show

**Current state** is always renderable, from any storage format. **Trajectory** (a burndown line,
progress over time) requires the store to retain history:

- A **patch-in-place ledger** overwrites state; it can only ever render *now*. Promising a trend
  chart over it is an error — there is nothing to chart.
- Trajectory needs an **append-only run-trace projection** (one snapshot/event per work step or
  per capture) or **transition timestamp columns**. Both are Step 2.4 / Step 4 decisions about the
  *store*, made upstream of any renderer.

So when the user asks for "progress over time," the question to ask is not about the chart — it is
*"does anything retain when transitions happened?"* If no, offer the current-state view now plus a
run-trace projection going forward, and say plainly that history starts the day the trace starts.

## Generic render-script kit

```
#!/usr/bin/env python3
# GENERATED-VIEW RENDERER for <logbook> — view = render(store). Pure, read-only, deterministic.
#   python3 <name>.render.py [--db PATH] [--out PATH] [--now ISO8601]
# `--now` is the query-time parameter (documented default), NOT the wall clock.

1. open store read-only
2. run the spec's queries verbatim:  funnel/partition, validation, dead-letter, summary
3. assert the partition sums to the row total      # the view must be impossible to render wrong
4. emit one self-contained file with a "GENERATED by <script> — do not edit" header
5. print output path + content hash               # two prints matching = determinism check
```

The assertion in step 3 matters: a render projection should *carry the completeness invariant
inside it*, so a store that violates the partition fails to render rather than rendering a lie.

If the design includes a run-trace, the capture step (`append one snapshot to the trace`) is its
own command — run after the workers, before the render. The render then reads ledger + trace,
both read-only.

The output file is committable (a snapshot export, rebuildable from the store at any time).
Whether the store and run-trace are committed follows Step 4's existing storage guidance — commit
diffable stores in shared repos; gitignore a live SQLite queue and commit an exported snapshot —
and note that an append-only run-trace is *not* rebuildable from a patch-in-place ledger: it is
the only history the system has. Record the decision in the spec.

## Spec section

When the probe fires, the spec's `## Storage` (or `## Physical stores`) section lists the render
projection alongside any others:

```markdown
- **Projection: <name> view** — role: `export-only` (render) — script `<name>.render.py` →
  `<name>.view.html` — renders the funnel/partition, validation, and dead-letter queries.
  Deterministic: pure function of the store; `--now` parameter, never wall clock; read-only.
  Temporal capability: <current-state only | trajectory via <run-trace / timestamps>>.
```

## Refresh cadence (handoff boundary)

The render script is passive, exactly like the logbook. *When* it re-runs — after each worker
batch, on a cron, on demand — is **skill-creator's job** (or a hook), the same boundary as the
driver poller. The spec gives the wiring everything it needs: script path, arguments, output path.

---

## Worked example (continuing work-queue.md's pipeline — do not copy the names)

The literature-review driver (`sources`: summarize → assess → verdict) gets a render projection
`review.render.py → review.view.html`:

- **Partition bar** — every source in exactly one bucket, by explicit precedence so the buckets
  cannot overlap: `parked` first (any `_status='failed'` or `verdict='needs-human'` — exactly the
  rows the spec's dead-letter query returns), then `skipped` (a terminal-skip outcome such as
  `'irrelevant'` or `'exclude'` — done-but-do-not-advance, per work-queue.md decision 5), then
  `done` (`verdict='include'`), then `in-flight` (unexpired lease), else `pending_<stage>`;
  asserts the buckets sum to `count(*)`. The partition query was added to the spec's `## Queries`
  first (rule 5) — the renderer renders it, it does not invent it.
- **Funnel** — the spec's funnel query, one bar per stage.
- **Dead-letter list** — parked rows with their attempt counts, for the human reviewer.
- **Row grid** — per-source stage cells colored by status, with a plain-language "why" derived
  from the row (`'irrelevant'` renders as *done-but-skipped*, never as *missing*).
- `--now` defaults to a documented fixed value used by the lease queries and the page's as-of
  stamp; the wall clock is never read. Rendering twice prints the same content hash.
- The ledger is patch-in-place, so the view is **current-state only** — the spec says so, and the
  page itself says "trajectory requires a run-trace" rather than faking a trend. If the user later
  wants the chart, a capture command appends per-stage counts to `review.history.jsonl` after each
  worker batch, and the render starts drawing the line from that day forward.

Every contract rule is visible: pure function (1), `--now` parameter (2), read-only with capture
split out (3), regenerated with a header (4), spec's own queries (5), one self-contained HTML
file (6).
