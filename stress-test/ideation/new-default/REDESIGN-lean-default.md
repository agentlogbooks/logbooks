# Redesign — the lean "capture-first" default

**Status:** draft / working copy. Nothing here is applied to the real plugin yet.
**Gate:** ✅ **PASSED.** The one contingent change (swapping `starter`'s 2-persona generation
for a single plain call as the *default*) was gated on the `plain-vs-starter` blind A/B
(`plainVsStarter.workflow.js`, `plain-vs-starter-result.json`). Result: plain **beats**
starter on substance (4.09 vs 3.88), **4/4 blind judges preferred plain**, with relevance
UP (4.5 vs 3.88) and mechanism diversity UP (distinct 13 vs 11.5); only novelty a hair lower
(3.38 vs 3.5). The +0.21 substance delta is within the ~0.3 noise band — so the honest claim
is "plain is at-least-as-good, unanimously preferred, more relevant and more diverse," not "a
big win." The bar (no quality loss from dropping the machinery) is decisively cleared.

**Attribution (don't over-claim).** The gate varied TWO things at once — architecture (one
self-deduping agent vs two *blind parallel* agents) and content (plain vs persona). The
diversity/convergence win is **architectural**: a single call sees its whole output and
can't emit cross-maker duplicates, whereas two blind persona agents collide on the obvious
answers by construction (re-confirming Track A). That validates the **single-call default** —
it does NOT show technique/persona *content* is bad. The on-demand techniques run
single-context on existing ideas, a regime this gate never tested. The one genuinely
persona-content effect is the relevance gap (4.5 vs 3.88): wild_card's "go wild" mandate
really does cost on-problem relevance. **Untested:** whether single-context + a technique
beats single-context plain. The import path, lazy framing, and the technique menu are strict
improvements that ship regardless.

## The move (user's words)

> Get ideas from something and just store them. If no ideas — just make one plain
> brainstorming LLM call, write them. Only if the user needs to iterate — we apply techniques.

Three default behaviors, replacing the current "frame-first generation machinery by default":

1. **Ideas supplied → capture them.** Store the user's own ideas; don't generate.
2. **No ideas → one plain brainstorm call.** No frame.discover checkpoint, no persona fan-out,
   no compare report. Just ideas, fast, on the wall.
3. **Techniques are opt-in.** The whole operator/persona/playbook toolkit stays — it just
   waits until the user asks to develop/iterate.

## Why (evidence from this stress-test)

- **Techniques don't earn being default.** Idea *substance* resisted five interventions
  (Track A prompt-tune, C structural prompts, D input-slice; see `QUALITY-LOOP-REPORT.md`).
  The frame+persona machinery does not out-produce a plain call on substance — so paying its
  latency/complexity up front buys nothing measurable. [Gate confirms head-to-head.]
- **Fixes the experience gap.** Time-to-first-idea drops from ~2.6 min + 2 user blocks to
  seconds (axes 1 & 2 of the UX stress-test).
- **Feeding ideas from a source is the validated missing flow** (idea #8 / user-leads). See
  `validation/VALIDATION-import-iterate-visualize.md`: FEED = *no* today; the planner falls
  through to `starter` and generates ~20 fresh ideas, silently ignoring the user's.

## What it repositions
The skill stops being "a fancy idea generator" and becomes **"a persistent idea logbook +
live wall + on-demand technique engine, seeded cheaply (by you or one call)."** The
differentiated value (persistence, visualization, lineage, the technique toolkit) all
survives — it relocates to where the evidence says it's actually earned.

---

## Exact SKILL.md changes

### 1. Invocation block (SKILL.md ~22-28) — add a capture/import form

```
ideation <topic-slug>: <intent>                      # primary — lean capture by default
ideation <topic-slug>: import these ideas: <list>    # NEW — store the user's own ideas
ideation <topic-slug> --import <file>: <intent>       # NEW — store ideas from a file
ideation <topic-slug> --techniques: <intent>          # NEW — opt in to the structured machinery (old starter)
ideation <topic-slug> --playbook <name>: <intent>    # force a specific playbook
ideation <topic-slug> --no-checkpoints: <intent>
ideation --list-topics
ideation <topic-slug> --show-state
```

### 2. Planner decision procedure (SKILL.md ~127-160) — reorder around capture

Replace step 3 ("topic is fresh") with this ordering. The **new default is lean capture**,
not `starter`:

```
3. Else if the topic is fresh (zero ideas in the logbook):

   3a. INGEST — if the intent SUPPLIES external ideas (a pasted list, "import these",
       "here are my ideas", "store/log these", or --import <file>):
       Plan = [ frame.discover (light)  →  generate.import source=<the ideas> ]
       No checkpoint, no compare. The user gave the ideas; just frame lightly (for the FK
       and for later iteration) and store them. generate.import auto-emits to the wall.

   3b. DEFAULT — lean capture (no ideas supplied, plain brainstorm intent):
       Plan = [ frame.discover (light)  →  generate.brainstorm count=12 ]
       ONE plain generation call (the dedicated lean generator that was A/B'd — NOT
       generate.fresh, whose frontmatter says "avoid_when: no clear hint"). No framing
       checkpoint, no persona fan-out, no compare report. Ends by offering the technique menu
       (Step 6). [Gate PASSED: plain ≥ starter, 4/4 judges prefer plain, relevance + diversity up.]

   3c. OPT-IN heavier shapes (only when the intent asks for them):
       - "techniques" / "structured" / "personas" / "frame it properly" / --techniques  → starter
       - "deep" / "thorough" / "full treatment" / "explore every angle"                 → deep_explore
       - "score" / "rank" / "prioritize formally"                                        → quick_seed
       - naming intent ("name X", "what should we call X", "rebrand")                    → naming
       - reframing a prior problem (topic already has a frame)                           → reframe_and_regenerate
```

Note the inversion: `starter` (frame.discover + 2 personas + compare) moves from **default**
to **opt-in under "techniques"**. Everything in 3c is unchanged in shape — only the trigger
moves from "fallthrough default" to "explicit opt-in".

### 3. Lazy framing (replaces mandatory frame-first)

- The capture default uses a **light frame** — `frame.discover` run cheaply (no
  context_scout, problem statement = the intent, minimal root-causes/HMW), purely to satisfy
  the not-null `frame_id_at_birth` FK and seed later iteration. No framing CHECKPOINT by
  default (the user didn't ask to shape the problem; they asked for ideas).
- **Frame-on-first-iterate.** When the user later runs a deep technique (`route`,
  `deep_explore`, scoring) on a lightly-framed topic, the planner inserts a real
  `frame.discover` (+ `CHECKPOINT: framing`) first: "before developing these, let me frame
  the problem properly." Real framing becomes opt-in, exactly where it pays off.

### 4. Discoverability — don't let "on-demand" become "out of sight"

The biggest risk of deferring techniques is that users never invoke them and the skill rots
into a note-taker. Mitigation: the lean default's **Step 6 close actively offers the menu**
(this already exists as "Try next" + operator followups — make it the prominent close):

```
12 ideas stored and on the wall. Want to go further?
- Score & rank them:            ideation <slug>: score and rank these
- Stress-test the strongest:    ideation <slug>: stress-test the top 3
- Find tensions / combine:      ideation <slug>: find tensions   |   hybridize 3 and 7
- Push the boldest wilder:      ideation <slug>: push idea 5 wilder
- Frame it properly & expand:   ideation <slug> --techniques
```

### 5. Wall wiring — already free
`generate.import` and `generate.fresh` are both `generate.*`, so the existing Step 5B
per-operator emit loop emits `idea_generated` per row automatically. Capture and import light
up the wall at ingest with **no new emit code** — this is precisely why import goes through an
operator, not the raw CLI (the validated gap: CLI/operators-without-the-orchestrator emit
nothing).

---

## What does NOT change
- Every operator, persona, zone, playbook stays exactly as-is. Power users who type
  `--techniques`, `deep`, `route`, `develop idea N`, `hybridize N and M` get today's behavior.
- The logbook schema, the wall, lineage, the audit trail — unchanged.
- The mechanism-first Description Writing Protocol (already adopted) — used by both
  `generate.fresh` and `generate.import`.

## Risks & mitigations
| Risk | Mitigation |
|---|---|
| Techniques deferred → never used (skill becomes a note-taker) | Step 6 menu offers them prominently after every capture |
| Plain call loses idea quality vs starter | **Gate PASSED** — plain ≥ starter (4/4 prefer plain, relevance + diversity up). No fallback needed |
| Light frame too thin for later deep work | Frame-on-first-iterate inserts a real `frame.discover` + checkpoint before heavy techniques |
| "import these" misread as a brainstorm request | Planner branch 3a keys on explicit ingest signals + `--import`; ambiguous cases still show the plan via AskUserQuestion before running |

## Files in this draft
- `generate.brainstorm.md` — the lean default generator (the exact prompt the A/B validated). Move to `operators/` on adoption.
- `generate.import.md` — the ingest operator. Move to `operators/` on adoption.
- this proposal — the SKILL.md edits (apply on adoption; gate has passed).
