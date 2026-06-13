# Ideation skill — ground-truth runtime observations

Empirical evidence gathered by actually running the CLI, the live wall, and a
faithful replay of the `starter` session. Every claim below is reproducible with
the harness in this directory (`wall_replay.py` + `scenarios/`). The synthesis
report must cite THIS file, not imagined journeys.

## A. Time-to-first-idea (axes 1 "smaller steps" & 2 "record first ideas")

`scenarios/timeline.jsonl` replays the **lightweight default** (`starter`
playbook: frame.discover → framing checkpoint → 2× generate.seed → decide.compare),
with conservative wall-clock-shaped gaps for subagent round-trips and human reads.

Measured sequence before the user sees a single concrete idea:

| t (s) | event | user-visible |
|------:|-------|--------------|
| 0 | session_started | title + 5 phase dots + empty board "Waiting for ideas…" |
| ~22 | plan_set | **USER BLOCK 1**: read plan in AskUserQuestion, click Accept |
| 22 | phase Frame + op frame.discover | placeholder card "running frame.discover" |
| ~70 | frame.discover returns + framing checkpoint | one "framing — Waiting for confirmation" card |
| ~70–101 | **USER BLOCK 2**: read frame, confirm framing | board still has ZERO ideas |
| 101 | phase Generate + 2 parallel op_started | two placeholder cards pulsing |
| **~156** | **first `idea_generated`** | **first real idea card finally appears** |
| ~203 | session_complete | 20 ideas, top-5 ranked |

**First concrete idea card appears at t ≈ 156 s (~2.6 min)** — after **2 user
interaction blocks** and **2 subagent round-trips**. On real Opus subagents these
gaps are typically longer. So even the "fast" default makes the user stare at a
near-empty wall for minutes. See `screenshots/current_state_empty.png` and
`screenshots/current_state_framing.png` — at the framing pause the entire board is
one small checkpoint card on black.

**Record-first feasibility:** `ideation_db.py` already exposes `add-idea` (single)
and `add-ideas-batch`. There is a direct path to write a raw idea in well under a
second — the flow simply never uses it before the framing+generation machinery.
Prior improvement topic already proposed this (ideas #4 ephemeral mode, #6 throwaway
sub-sessions, #8 "user leads, agent interrupts", #12 "input buffer for intent").

## B. Dynamism-when-populated (axis 3 "better visualisation")

Current wall (`live/view.html`) renders cards in **insertion order** and never
moves them. Evidence:

- `screenshots/current_state_scored.png` — 20 ideas, all scored. Cards stay in
  arrival order; the rank-1 idea (#8) sits mid-grid. Score is an inert number in
  the corner. No sort, no heat, no size/weight encoding. To find the winners you
  must read all 20 numbers.
- `screenshots/current_state_churn.png` — cut ideas remain in place, faded +
  strikethrough, interleaved with live ones → clutter.
- `screenshots/current_state_80.png` — `deep_explore` peak. 80 near-identical
  yellow stickies in a flat scroll. Kind is a tiny dot; cuts blend in; the 5
  ranked winners are invisible in the crowd. The board does not help you navigate.

The only motion in the current wall is: card pop-in on arrival, placeholder pulse,
and the live-dot blink. Once ideas exist, the board is **static** — the literal
gap the user named ("more dynamic when something there").

### Prototype A/B (this directory's `view.dynamic.html`)

Same SSE event contract (drop-in). Adds, all driven by existing events:

- **Reorder-on-score with FLIP motion** — `idea_scored` reflows cards into score
  order; winners float to top-left. `screenshots/dynamic_state_scored.png` vs
  `current_state_scored.png`.
- **Score → heat bar** on each card (width + warm/cool colour) — strength is
  visible without reading numbers.
- **Rank badges + winners band** — ranked ideas carry `#1…#5` and a gold ring.
- **Cut → compost tray** — `idea_cut` slides the card into a collapsed
  "N cut — set aside" tray, leaving a clean board.
  `screenshots/dynamic_state_churn.png`.
- **Streaming pulse / newest-glow + live activity line** — each arrival flashes
  and the header narrates ("💡 <title>", "🏆 #1 — <title>"), so it feels alive
  while ideas land.
- At 80 ideas the dynamic board is score-sorted + heat-encoded + winners-first →
  navigable. `screenshots/dynamic_state_80.png` vs `current_state_80.png`.

The prototype stays vanilla HTML/JS/SSE — no libraries — matching the existing wall.

## C. Cross-session persistence is fragile (notable finding, not the lede)

- `ideation_db.py` resolves topics to `<git-root>/.logbooks/ideation/<slug>/`
  (`IDEATION_DIR = ".logbooks/ideation"`).
- The repo's actual committed dogfood logbooks live at `.ideation/<slug>/`
  (68 git-tracked files: `grow-afternoon-revenue`, `ideation-skill-improvements`,
  `code-review-skill`).
- Result: `ideation_db.py list-topics` → `[]`. `show-state ideation-skill-improvements`
  → nothing. **Every prior topic is invisible to the current CLI.**
- Git history shows the path was refactored (`538accd` "use hidden ./.logbooks/",
  `dbc4179` "consolidate plugin storage") with **no migration**. The change shipped.
- The skill's headline promise is "ideas persist across sessions; follow-up prompts
  resume where the last one ended." A returning user who upgrades past that refactor
  silently loses access to every topic and would be told "topic doesn't exist —
  create it?" — re-running brainstorms they already paid for.
- `live/emit.py` and `live/serve.py` independently hardcode `.logbooks/ideation/`,
  so the wall path and the CLI path can diverge with no shared constant.

## D. logbook-creator conclusions seed (the skill that designed this logbook)

- `logbook-creator/references/concept.md`'s worked **"Ideation logbook"** example is
  a flat **CSV**: `id, name, description, source_agent, phase, tag, ICE scores`.
- The actual ideation implementation is a **multi-entity SQLite** logbook
  (`topic_meta, frames, facts, ideas, lineage, assessments, operator_runs`) + a
  JSONL **run-trace** projection (`live-events.jsonl`) + the **live wall** as an
  export-only **visualisation projection**.
- So the concept *understates* what a serious "deep ideation" logbook becomes — the
  exact gap the concept's own "deep workflows need logbooks" section gestures at.
- `concept.md` lists **"Visualize"** as a first-class action and names projections
  (run-trace / export-only / mirror). But the **logbook-creator SKILL.md flow**
  (Steps 1–5) barely walks the user through designing a visualization/projection —
  it's an optional aside in Step 4. Yet the live wall is the ideation skill's single
  best UX feature. logbook-creator under-serves its own best action.
- The address-migration failure in §C is a direct violation of concept.md's own
  **"Logbook address"** rule ("a stable reference that works across sessions… when
  the user moves this file, update the address here") — there was no stable,
  migrated address across the refactor.

## Reproduce

```bash
cd stress-test/ideation
python3 gen_scenarios.py                 # regenerate scenarios/
python3 wall_replay.py --events scenarios/timeline.jsonl --cadence 0.4 \
    --html ../../plugins/ideation/skills/ideation/live/view.html   # watch the current wall live
python3 wall_replay.py --events scenarios/state_80.jsonl \
    --html view.dynamic.html             # eyeball the prototype at peak load
```
