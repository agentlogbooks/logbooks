#!/usr/bin/env python3
"""
gen_scenarios.py — synthesize event streams for the ideation live-wall stress test.

Writes faithful `.logbooks/...live-events.jsonl`-shaped streams into scenarios/:

  timeline.jsonl       A realistic `starter` playbook session with wall-clock-shaped
                       ts gaps. Replay with `--cadence 0` to honour the gaps via the
                       harness, or read the gaps directly to reason about
                       time-to-first-idea. This is the SPINE evidence for axes 1 & 2.

  state_empty.jsonl    What the user sees first: title + phases + plan rail, no ideas.
  state_framing.jsonl  Frame op in flight + framing checkpoint pause card (user waits).
  state_3.jsonl        First generate op returned — 3 cards.
  state_20.jsonl       `starter` end state — 20 seeds, compare ranks top 5.
  state_scored.jsonl   20 ideas all scored (drives re-rank/reorder dynamism test).
  state_churn.jsonl    Mixed board — scores + kept + cut (drives cut-animate-out test).
  state_80.jsonl       `deep_explore` peak — 80 ideas, mixed kind/tag/score/status.
  state_failure.jsonl  A failed op card + a pending checkpoint (degraded states).

Each state file is CUMULATIVE: the harness hydrates from offset 0, so loading any
one renders that exact end state — deterministic for screenshots.
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "scenarios"
OUT.mkdir(parents=True, exist_ok=True)
SLUG = "cafe-afternoon-revenue"
PHASES = ["Frame", "Generate", "Transform", "Evaluate", "Decide"]

# --- content pool (coffee-talk style, concrete) ------------------------------
TAGS = ["BOLD", "WILD", "SAFE"]
SEEDS = [
    ("Loyalty happy-hour after 2pm", "Punch-card that only fills on weekday afternoons, so regulars learn the slow hours are the cheap hours and start drifting in then."),
    ("Laptop-corner day pass", "Sell a $6 afternoon pass for a quiet corner with outlets and fast wifi; the coffee's extra, the seat is the product."),
    ("Pastry rescue box", "Bag up the morning's unsold pastries at 3pm for half price; turns waste into a reason to walk in after lunch."),
    ("Second-cup half-price token", "Anyone who bought a morning coffee gets a token for a half-price afternoon refill, redeemable same day only."),
    ("Neighborhood remote-work club", "A monthly membership that reserves afternoon seating and a bottomless drip, aimed at the work-from-home crowd nearby."),
    ("Kids draw, parents stay", "Free crayons and a wall to pin drawings on; parents on the school run linger and order a second drink."),
    ("Afternoon tasting flight", "Three 4oz pours of single-origin for the price of a latte, framed as a slow-hour ritual, not a rush purchase."),
    ("Bring-a-friend 3-to-5", "Between 3 and 5, two drinks ring up as one-and-a-half; the empty room fills because nobody comes alone."),
    ("Standing pre-order for offices", "Nearby offices set a recurring 3pm tray order; you batch-make it, they expense it, the lull disappears."),
    ("Silent-hour study deal", "Declare 2-4pm phone-free and discount drip 30%; the vibe itself becomes the draw for students."),
    ("Cold-brew growler refills", "Sell branded growlers, refill cold brew cheap in the afternoon; regulars stock their fridge and your slow hours move volume."),
    ("Barista's-choice mystery cup", "A $3 afternoon-only mystery drink the barista improvises; cheap experiment that turns dead time into a game."),
    ("Afterschool hot-chocolate route", "Partner with the school two blocks over for a hot-chocolate punch card kids redeem walking home."),
    ("Co-working stamp partnership", "Tie up with a co-working space: their members flash a badge for afternoon discounts, you get their overflow."),
    ("Slow-hour catering sampler", "Use the lull to bake mini catering samplers and hand them to office managers who walk past at 3."),
    ("Pay-what-it-weighs cookies", "Afternoon cookies priced by the gram on a little scale at the counter; novelty pulls the curious in."),
    ("Reverse rush-hour playlist", "A posted live DJ-style afternoon playlist; people come for the set, the coffee is incidental."),
    ("Two-for-Tuesday iced drinks", "Every Tuesday afternoon, iced drinks are buy-one-gift-one; the gifted one drags in a new face."),
    ("Window-seat reservation app", "Let people reserve the good window seat for an afternoon hour for a small fee that's redeemable on food."),
    ("Local-maker pop-up shelf", "Rent a shelf to a local maker who hosts an afternoon demo; their followers become your 3pm traffic."),
]
VARIANTS = [
    "Push it wilder — what if it ran all week, not just afternoons?",
    "Ground it — tie the trigger to the existing POS punch-card so staff do nothing new.",
    "Pressure-test — who hates this, and what breaks at 50 covers?",
    "Cross it with the loyalty app so the token lives on a phone, not paper.",
    "Invert it — instead of discounting, make the slow hour feel exclusive and charge more.",
]
HYBRIDS = [
    "Loyalty pass × tasting flight — members get one free afternoon flight a week.",
    "Pastry rescue × office pre-order — surplus pastries auto-bundle into the 3pm office tray.",
    "Silent hour × co-working badge — phone-free study room that co-workers can book.",
    "Mystery cup × bring-a-friend — the mystery drink is free if you bring someone new.",
]


def ev(t, type_, payload):
    return {"ts": round(t, 2), "type": type_, "payload": payload}


def idea(i):
    pool = SEEDS
    kind, src = "seed", pool[(i - 1) % len(pool)]
    if i > 20 and i <= 60:
        kind = "variant"
        base = SEEDS[(i - 1) % len(SEEDS)]
        src = (base[0] + " — variant", VARIANTS[(i - 1) % len(VARIANTS)])
    elif i > 60:
        kind = "hybrid"
        src = (HYBRIDS[(i - 1) % len(HYBRIDS)].split(" — ")[0], HYBRIDS[(i - 1) % len(HYBRIDS)])
    title = src[0].replace("&apos", "'").replace("nbsp;", " ")
    return {"id": i, "title": title, "description": src[1],
            "kind": kind, "tag": TAGS[(i * 7) % 3], "status": "active"}


def plan_steps():
    return [
        {"n": 1, "type": "op", "description": "Identify root causes and framing questions"},
        {"n": 2, "type": "checkpoint", "description": "Confirm the framing"},
        {"n": 3, "type": "parallel", "description": "Generate ~20 diverse ideas in parallel"},
        {"n": 4, "type": "op", "description": "Present them side-by-side in a short report"},
    ]


def header():
    return [
        ev(0, "session_started", {"topic": SLUG, "phases": PHASES}),
        ev(0.2, "plan_set", {"steps": plan_steps()}),
    ]


def write(name, events):
    p = OUT / name
    with p.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    print(f"wrote {p.name:22} {len(events):>3} events")


# --- timeline: realistic starter session, ts in seconds ----------------------
def timeline():
    e = []
    t = 0.0
    e.append(ev(t, "session_started", {"topic": SLUG, "phases": PHASES}))
    t += 22  # user reads plan-approval AskUserQuestion, accepts
    e.append(ev(t, "plan_set", {"steps": plan_steps()}))
    t += 0.3
    e.append(ev(t, "phase_started", {"name": "Frame"}))
    e.append(ev(t, "op_started", {"op_run_id": 1, "operator": "frame.discover", "persona": "",
                                  "cohort_size": 0, "step_n": 1,
                                  "description": "Identify root causes and framing questions"}))
    t += 48  # frame.discover subagent round-trip (web-less but still a full agent)
    e.append(ev(t, "op_finished", {"op_run_id": 1, "status": "succeeded", "ideas_count": 0}))
    e.append(ev(t, "checkpoint_reached", {"name": "framing", "step_n": 2}))
    t += 31  # user reads the frame, confirms
    e.append(ev(t, "checkpoint_resolved", {"name": "framing", "action": "proceed"}))
    t += 0.3
    e.append(ev(t, "phase_started", {"name": "Generate"}))
    e.append(ev(t, "op_started", {"op_run_id": 2, "operator": "generate.seed", "persona": "innovator",
                                  "cohort_size": 0, "step_n": 3, "description": "Practical ideas — 10"}))
    e.append(ev(t, "op_started", {"op_run_id": 3, "operator": "generate.seed", "persona": "wild_card",
                                  "cohort_size": 0, "step_n": 3, "description": "Wild ideas — 10"}))
    t += 54  # parallel generate subagents — FIRST IDEA APPEARS HERE
    first_idea_t = t
    for i in range(1, 11):
        e.append(ev(t + i * 0.05, "idea_generated", idea(i)))
    e.append(ev(t + 1.0, "op_finished", {"op_run_id": 2, "status": "succeeded", "ideas_count": 10}))
    t += 6
    for i in range(11, 21):
        e.append(ev(t + i * 0.05, "idea_generated", idea(i)))
    e.append(ev(t + 1.5, "op_finished", {"op_run_id": 3, "status": "succeeded", "ideas_count": 10}))
    t += 4
    e.append(ev(t, "phase_started", {"name": "Decide"}))
    e.append(ev(t, "op_started", {"op_run_id": 4, "operator": "decide.compare", "persona": "",
                                  "cohort_size": 20, "step_n": 4, "description": "Side-by-side compare"}))
    t += 34
    for rank, iid in enumerate([8, 3, 11, 1, 17], start=1):
        e.append(ev(t + rank * 0.1, "idea_ranked", {"id": iid, "rank": rank}))
    e.append(ev(t + 1.0, "op_finished", {"op_run_id": 4, "status": "succeeded", "ideas_count": 0}))
    t += 3
    e.append(ev(t, "session_complete", {}))
    print(f"\n  >> timeline: first idea card at t={first_idea_t:.0f}s "
          f"({first_idea_t/60:.1f} min); session_complete at t={t:.0f}s")
    return e


# --- cumulative state snapshots ----------------------------------------------
def state_empty():
    return header()


def state_framing():
    e = header()
    e.append(ev(1, "phase_started", {"name": "Frame"}))
    e.append(ev(1, "op_started", {"op_run_id": 1, "operator": "frame.discover", "persona": "",
                                  "cohort_size": 0, "step_n": 1,
                                  "description": "Identify root causes and framing questions"}))
    e.append(ev(2, "op_finished", {"op_run_id": 1, "status": "succeeded", "ideas_count": 0}))
    e.append(ev(2, "checkpoint_reached", {"name": "framing", "step_n": 2}))
    return e


def state_n(n, scored=False, ranked=None, kept=None, cut=None, phase="Generate"):
    e = header()
    e.append(ev(1, "phase_started", {"name": phase}))
    for i in range(1, n + 1):
        e.append(ev(1 + i * 0.01, "idea_generated", idea(i)))
    if scored:
        # spread scores so re-rank is visible
        for i in range(1, n + 1):
            sc = 40 + ((i * 37) % 56)
            e.append(ev(3 + i * 0.01, "idea_scored",
                        {"id": i, "score": sc, "rationale": "Scored on reach × effort × margin."}))
    for r, iid in enumerate(ranked or [], start=1):
        e.append(ev(5 + r * 0.05, "idea_ranked", {"id": iid, "rank": r}))
    for iid in kept or []:
        e.append(ev(6 + iid * 0.01, "idea_kept", {"id": iid}))
    for iid in cut or []:
        e.append(ev(6 + iid * 0.01, "idea_cut", {"id": iid, "stress_note": "Thin margin; cannibalizes the morning rush."}))
    return e


def state_failure():
    e = header()
    e.append(ev(1, "phase_started", {"name": "Generate"}))
    e.append(ev(1, "op_started", {"op_run_id": 2, "operator": "generate.seed", "persona": "innovator",
                                  "cohort_size": 0, "step_n": 3, "description": "Practical ideas — 10"}))
    for i in range(1, 6):
        e.append(ev(2 + i * 0.01, "idea_generated", idea(i)))
    e.append(ev(3, "op_finished", {"op_run_id": 2, "status": "succeeded", "ideas_count": 5}))
    e.append(ev(3, "op_started", {"op_run_id": 3, "operator": "validate.web_stress", "persona": "",
                                  "cohort_size": 5, "step_n": 4, "description": "Stress-test top 5 on the web"}))
    e.append(ev(5, "op_finished", {"op_run_id": 3, "status": "failed",
                                   "error": "web search timed out after 2 retries"}))
    e.append(ev(5, "checkpoint_reached", {"name": "before_decide", "step_n": 5}))
    return e


if __name__ == "__main__":
    write("timeline.jsonl", timeline())
    write("state_empty.jsonl", state_empty())
    write("state_framing.jsonl", state_framing())
    write("state_3.jsonl", state_n(3))
    write("state_20.jsonl", state_n(20, ranked=[8, 3, 11, 1, 17], phase="Decide"))
    write("state_scored.jsonl", state_n(20, scored=True, ranked=[8, 3, 11, 1, 17], phase="Decide"))
    write("state_churn.jsonl", state_n(24, scored=True, ranked=[8, 3], kept=[8, 3, 11], cut=[5, 13, 20, 16], phase="Decide"))
    write("state_80.jsonl", state_n(80, scored=True, ranked=[8, 3, 64, 41, 72],
                                    kept=[8, 3, 64], cut=[5, 13, 20, 33, 47, 51], phase="Decide"))
    write("state_failure.jsonl", state_failure())
