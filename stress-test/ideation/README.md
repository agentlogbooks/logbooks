# Ideation skill — usability stress test

A reusable harness + a captured run that stress-tests the **experience** of the
`ideation` skill (not its functional correctness), focused on three axes the wall
makes or breaks:

1. **Start with smaller steps** — how long until the user does something useful.
2. **Record first straight ideas** — capturing raw ideas immediately.
3. **Better, more dynamic visualisation** — what the live wall does once it's populated.

It also captures conclusions about the `logbook-creator` skill, since ideation is a
worked example of a logbook.

## What's here

| File | What it is |
|---|---|
| `wall_replay.py` | Reusable replay server. Serves ANY view HTML + replays ANY event stream over the same `/events` SSE contract the real `live/serve.py` uses. A/B the current wall vs a prototype, or replay a real captured session. |
| `gen_scenarios.py` | Generates `scenarios/` — a realistic `starter` **timeline** (to measure time-to-first-idea) plus cumulative **state snapshots** for deterministic screenshots. |
| `scenarios/*.jsonl` | Synthetic event streams: `timeline`, `state_empty/framing/3/20/scored/churn/80/failure`. Same shape as `.logbooks/ideation/<slug>/live-events.jsonl`. |
| `view.dynamic.html` | **Dynamic-viz prototype** — drop-in for `live/view.html` on the same event contract. Adds reorder-on-score (FLIP), score heat bars, rank badges, a compost tray for cuts, and a streaming activity line. Vanilla HTML/JS/SSE, no libraries. |
| `screenshots/current_*.png` vs `dynamic_*.png` | A/B evidence of every state. |
| `observations.md` | Ground-truth runtime findings (timeline numbers, the persistence bug, the logbook-creator seed). The report cites this. |
| `STRESS-TEST-REPORT.md` | The synthesized findings + recommendations + logbook-creator conclusions. |

## Reproduce

```bash
cd stress-test/ideation
python3 gen_scenarios.py        # (re)generate scenarios/

# Watch the CURRENT wall replay the starter session live (honouring time gaps):
python3 wall_replay.py --events scenarios/timeline.jsonl --cadence 0.4 \
    --html ../../plugins/ideation/skills/ideation/live/view.html
# open http://127.0.0.1:7879

# Eyeball the PROTOTYPE at peak load (80 ideas, sorted/heat/compost):
python3 wall_replay.py --events scenarios/state_80.jsonl --html view.dynamic.html
```

`--cadence 0` dumps all events on connect (snapshot — used for screenshots);
a positive cadence streams them one-by-one for a live feel.

### Re-capture screenshots

```bash
# example: one state, current wall
python3 wall_replay.py --events scenarios/state_scored.jsonl \
    --html ../../plugins/ideation/skills/ideation/live/view.html --port 7881 &
playwright screenshot http://127.0.0.1:7881 screenshots/current_state_scored.png \
    --full-page --wait-for-timeout 2200
```

## Replaying a REAL session

The harness reads the exact on-disk event format, so you can replay any real run:

```bash
python3 wall_replay.py --events ../../.logbooks/ideation/<slug>/live-events.jsonl
```

## Note on scope

This is a UX/experience harness. It drives the wall through synthetic and real event
streams; it does not spawn the planner/operator subagents. The faithful `timeline`
encodes conservative wall-clock gaps for those round-trips so time-to-first-idea is
representative, not exact.
