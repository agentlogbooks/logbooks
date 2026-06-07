# Ideation — Output-Quality Stress Test (5× improve loops)

Two `generate/render → judge → improve → re-measure` loops, 5 rounds each, run as
separate background workflows. Track A iterated the skill's **idea-generation
prompts**; Track B iterated the **dynamic-viz prototype** (`view.dynamic.html`). Both
iterated on **working copies** — the shipping plugin files were never touched.

Full machine output: `quality-loop/track-a-result.json`, `quality-loop/track-b-result.json`.

## TL;DR

- **The honest result is the blind A/B, not the in-loop trajectory.** In a loop where
  the same model generates, judges, and improves, a rising in-loop score is Goodhart
  noise (the improver teaches to the judge). So each loop ends with a **blind A/B**:
  round-1 vs round-5, labels stripped, judged by a fresh loop-unaware instance,
  position-swapped to cancel order bias.
- **Track A (idea quality): iteration did NOT help — it slightly regressed.** Blind
  A/B substance round-1 **4.0** vs round-5 **3.5** (compliance tied 4.0/4.0); the two
  blind judges preferred round-1 or called it a tie. Five rounds of prompt-wordsmithing
  did not improve idea quality.
- **Track B (viz): iteration DID help, modestly.** Blind A/B ux baseline **3.25** vs
  final **3.75** (+0.5), but the two swapped judges **split** (one preferred final, one
  baseline) — a real but contested gain.
- **The meta-finding (most valuable):** the self-improvement loop paid off on the
  **concrete, visually-verifiable** artifact (the wall) and failed on the **open-ended
  generative** one (idea substance). Where the judge can point at a pixel-level defect
  and the improver can fix exactly that, the loop converges; where "quality" is
  diffuse novelty/diversity, the improver just reshuffles wording and can narrow the
  idea space while chasing the rubric.
- **Track A's payoff was diagnostic.** Every one of the 5 rounds independently flagged
  the same prompt-resistant weakness: **personas collapse to the same obvious moves**
  (innovator and wild_card produce near-duplicate sets; within a set, ~half the ideas
  fold into one mechanism). Wording never fixed it — the fix is structural.

## Method (both tracks)

- **Working copies only.** Track A edited copies in `quality-loop/track-a/prompts/`
  (`generate.seed.md`, `output-rules.md`, `innovator.md`, `wild_card.md`); Track B
  edited `view.dynamic.html` with a per-round snapshot in `quality-loop/track-b/rounds/`.
  The real plugin (`plugins/ideation/...`) is untouched — adopt nothing unless it earns it.
- **Round-blind dual judges** averaged per round (fights run-to-run variance).
- **Compliance vs Substance split** (Track A): compliance (coffee-talk, has-example,
  no-jargon) is trivially gameable; substance (novelty, mechanism-specificity,
  relevance, diversity) is the prize. Reported separately; substance watched.
- **Anti-overfit constraints on the improver:** general edits only (never tuned to the
  eval topics), preserve persona voice + terseness, hard byte caps to prevent bloat.
- **Resilience:** a failed agent reuses the prior round's file; a failed render falls
  back to judging code.
- **Track A eval set:** 2 fixed frames (cafe afternoon revenue; B2B SaaS early churn)
  × 2 personas (innovator, wild_card) × 8 ideas = 32 ideas/round, identical frames
  every round to isolate the prompt as the only variable.
- **Honest scope (Track A):** the harness isolates the `generate.seed` *prompt*. Base
  model capability is constant across rounds and dominates idea quality, so this
  measures a **prompt delta, not a skill delta** — and the blind A/B is what says
  whether even that prompt delta is real.

---

## Track A — idea-output quality

### In-loop trajectory (round-blind dual judges, 1–5)

| Round | Compliance | Substance |
|------:|:----------:|:---------:|
| 1 | 4.79 | 3.85 |
| 2 | 4.75 | 3.59 |
| 3 | 4.44 | 3.56 |
| 4 | 4.53 | 3.87 |
| 5 | 4.66 | 3.76 |

Substance bounced in noise (3.56–3.87) with no upward trend; compliance actually
**declined** (4.79 → 4.66). Notably, the gameable metric didn't even climb — the
improver's edits weren't effective at gaming the judge, let alone improving substance.

### Blind A/B (the honest result) — round-5 did NOT beat round-1

| | Substance | Compliance |
|---|:--:|:--:|
| Round 1 | **4.0** | 4.0 |
| Round 5 | **3.5** | 4.0 |

Swapped blind judges: one preferred **round-1** on substance, one called it a **tie**.
Their reasons: round-1 fielded a more diverse lock-in/switching-cost cluster, while
round-5 had **collapsed roughly half its SaaS ideas into near-duplicate
onboarding-activation variants** — i.e. the improver's push toward "attack the stated
root cause" narrowed the idea space and *cost* diversity.

**Verdict: do not adopt the round-5 prompts.** (The real plugin is unchanged; working
copies grew only modestly within the byte caps — generate.seed 5473→6224,
output-rules 9435→9911, innovator 3152→3530, wild_card 2912→3571.)

### The durable, prompt-resistant weakness (every round flagged it)

The diagnostic value is real and consistent. Across all 5 rounds the judges repeated:

- **Cross-persona convergence.** innovator and wild_card independently produce the same
  moves (cafe: rent the ovens, morning-receipt return ticket, quiet study room,
  declining-price pastry, guest baker; B2B: data lock-in, churn-signal human outreach,
  hours-saved counter). "When a systematic persona and a maximize-surprise persona land
  the same idea unprompted, that is direct evidence the idea is obvious" — and that the
  persona axis adds little real divergence (wild_card mostly re-skins innovator with
  louder similes).
- **Within-set mechanism clustering.** ~half of an 8-idea set folds into one lever
  ("make value visible", "raise switching cost", "rent the empty space").
- **Relevance vs the hard constraint.** Cafe ideas that recover waste margin or train
  regulars to defer to a cheap afternoon window flirt with the morning cannibalisation
  the frame forbids.

### Track A conclusion + recommendation

Idea quality is gated by something **prompt wording can't move**: weak structural
differentiation between personas and no divergence/dedup pressure. The in-ecosystem
fixes that would actually help (and that this loop could NOT achieve by editing prose):

1. **Make personas structurally non-overlapping**, not just tonally different — e.g.
   give each persona a disjoint mechanism bank / stimulus source so two personas can't
   land the same move. (Today innovator=SCAMPER/TRIZ and wild_card=random-stimulus
   still converge because both reach for the obvious answer first.)
2. **Add an explicit divergence/dedup step** to `generate.seed` (or a light orchestrator
   pass): after drafting, drop or rewrite any idea whose mechanism duplicates one already
   in the batch — the convergence the judges flagged is mechanical and detectable.
3. **Don't over-weight "relevance"** in generation guidance — round-5 showed it trades
   away the novelty/diversity that is the actual prize.

These are structural changes to the operator/persona design, not prompt tweaks — which
is exactly why a 5× prose-editing loop couldn't reach them.

---

## Track B — dynamic-viz prototype quality

### In-loop trajectory (1–5)

| Round | UX | Code | render |
|------:|:--:|:----:|:------:|
| 1 | 3 | 4 | ok |
| 2 | 4 | 5 | ok |
| 3 | 4 | 4 | ok |
| 4 | 4 | 4 | ok |
| 5 | 4 | 5 | ok |

UX rose 3→4 after round 1 then plateaued; code stayed 4–5.

### Blind A/B (the honest result) — final modestly beats baseline

| | UX (blind) |
|---|:--:|
| Baseline (round-0 = original prototype) | **3.25** |
| Final (round-5) | **3.75** |

Swapped judges **split**: one preferred final, one baseline. Both agreed the decisive
factor is the **populated state**: the final **color-grades the whole card by score
tier** (gold winners at top → muted/purple cuts at bottom), adds a **winners band**,
**score-band dividers**, and **kind chips**, so the 80-idea board is scannable top to
bottom in one glance (`quality-loop/track-b/rounds/blind-final/80.png`) versus the
baseline's uniform-amber wall where winners are lost. The dissent: the baseline's
empty/framing states were better centered.

### What the loop added (round-0 → final, 445 → 616 lines)

Whole-card score-heat tinting (not just a 4px bar); a pinned winners band; score-band
dividers (90s/80s/70s/<70) chunking the long tail; visible **kind chips** (dot + label)
so seed/variant/hybrid survives the heat repaint; centered empty/framing states.
**Stayed in-ecosystem:** all 13 SSE handlers intact, `EventSource('/events')` intact,
no external libraries/CDNs introduced — still a drop-in for `live/view.html`.

### Still open (round-5 judge, real and unfixed)

1. **Kind illegible on scored cards** — once heat tints the background, kind collapses
   to a 9px dot; keep the text kind-label or add a kind-colored left edge stripe.
2. **Score-band dividers + compost bar too low-contrast** (#6a5a30/#7a5c40 on dark) —
   brighten labels, add a per-band rule/tint, make the cut tray read as clickable.
3. **Mid-pack heat too subtle when scores bunch** — widen the lightness/contrast delta
   across the ramp so within-tier ranking is visible, not just the extremes.

### Track B conclusion + recommendation

**Keep the final** `view.dynamic.html` (modestly better, in-ecosystem, drop-in-clean),
then apply the 3 open fixes — they're concrete and screenshot-verifiable, exactly the
kind of thing this loop is good at. `round-0.html` is preserved if you want to revert.

---

## The meta-finding: where a self-improvement loop pays off

| | Track A (idea substance) | Track B (viz) |
|---|---|---|
| Artifact | open-ended generative output | concrete visual UI |
| Judge can point at the defect? | no — "novelty" is diffuse | yes — "winners not scannable" |
| Improver can fix exactly that? | no — only reshuffles wording | yes — edit the CSS/JS |
| Blind A/B result | **regressed** (4.0→3.5 substance) | **improved** (3.25→3.75 ux) |
| Loop's real value | diagnostic (named the structural flaw) | incremental (real polish) |

Run a generate→judge→improve loop when the artifact is **concrete and the judge's
feedback is actionable at the level the improver edits**. For open-ended generative
quality, the loop's value is **diagnosis, not optimization** — and you only learn which
case you're in by running a **blind A/B**, never by trusting the rising in-loop score.

## Next moves

- **Ideation idea quality:** the wins are structural, not prose — disjoint persona
  mechanism banks + a divergence/dedup pass in `generate.seed`. Do NOT adopt the
  round-5 working prompts. (Re-run this harness after a structural change to measure it
  the same way.)
- **Viz:** adopt the final `view.dynamic.html`, then fix the 3 open round-5 issues; it
  remains a clean drop-in for `live/view.html`.
- **Methodology:** keep blind-A/B + compliance/substance split + anti-overfit caps as
  the standard for any future self-improvement loop in this repo.

## Artifacts

```
stress-test/ideation/quality-loop/
  rubric.md                     split compliance/substance rubric (grounded in output-rules.md)
  track-a/frames.json           the 2 fixed eval frames
  track-a/prompts/*.md          round-5 working prompts (NOT for adoption)
  track-a-result.json           trajectory + blind A/B + per-round weaknesses
  track-b/rounds/round-0.html   baseline prototype
  track-b/rounds/round-N.html   per-round snapshots
  track-b/rounds/round-N/*.png  per-round screenshots (5 states each)
  track-b/rounds/blind-{baseline,final}/*.png   blind A/B screenshot sets
  track-b-result.json           trajectory + blind A/B + per-round issues
  trackB.workflow.js            the Track B workflow (re-runnable)
../view.dynamic.html            the FINAL improved prototype (current)
  track-c/prompts-base/*.md      control = real baseline prompts
  track-c/prompts-fix/*.md       the structural fix (NOT for adoption — see Track C)
  track-c-result.json            base-vs-fix blind A/B + convergence census
```

---

# Track C — the structural fix tested (and what actually moves the needle)

Track A concluded that idea-quality gains are *structural, not prose* and recommended
"disjoint persona mechanism banks + a divergence/dedup pass." Track C **built that fix
and measured it.** It does not work — and the way it fails is the most useful result in
this whole exercise.

## The fix (prototype, in `quality-loop/track-c/prompts-fix/`, real plugin untouched)

Three structural additions to the generation prompts:
1. **Disjoint territory lanes** — innovator owns *re-engineering the existing thing*;
   wild_card owns *random/absurd stimulus + perspective-raids* (kept distinct from the
   connector persona's rational cross-domain analogy).
2. **Hard "ban the obvious five" gate** — each persona must list and forbid the five most
   predictable answers before generating (today it's a soft nudge wild_card under-honors).
3. **Within-batch divergence pass** in `generate.seed` — label each idea's core mechanism,
   ensure all distinct, drop duplicates.

## Measurement: clean baseline-vs-fix blind A/B (n=2 frames, 2 personas, 8 ideas/cell)

Substance broken into novelty / mechanism / relevance (the advisor's discriminator),
position-swapped blind judges, plus a joint-labeled convergence census as a manipulation
check. **Verdict bar: fix beats baseline on substance with relevance flat-or-up.**

| Axis | Baseline | Fix | Δ |
|---|:--:|:--:|:--:|
| Novelty | 3.25 | **4.0** | **+0.75** |
| Mechanism | 4.0 | 3.75 | −0.25 |
| Relevance | 4.25 | **3.75** | **−0.5** |
| **Substance (nov+mech+rel)** | **3.83** | **3.83** | **0.0** |
| Compliance | 4.5 | 4.5 | 0.0 |

Blind judge preference: **3 of 4 preferred baseline.** → **Fails the bar: substance flat,
relevance down.**

## Why it fails — the predicted mirror of Track A

The fix raised *surface* novelty (+0.75) by **buying it at the cost of relevance** (−0.5).
The blind judges, every time, said the same thing: the fix's boldest ideas are
**"vibe/positioning"** ("chase the 4 o'clock light", "slowest cafe in town") with no real
revenue engine, or operationally-heavy gimmicks ("laser-etched keepsake card",
"break-room hardware glass", "coffee wager") only loosely tied to the stated problem.
Baseline stayed concrete and root-cause-anchored. Track A over-weighted relevance and
killed diversity; Track C over-weighted distinctness and killed relevance. Same swap,
opposite direction.

## The deeper finding — the diversity lever never engaged

The convergence census (manipulation check) is decisive. With rigorous joint
mechanism-labeling (prose stripped to the core move), the fix was **equal-or-LESS**
mechanically diverse than baseline:

| | Baseline distinct / collisions | Fix distinct / collisions |
|---|:--:|:--:|
| cafe | 9 / 4 | **8 / 5** |
| B2B | 9 / 4 | 9 / 3 |

The census note, verbatim: *"the diversity-intervention signature (distinct spiking from
generous splitting) does not hold up… more vividly FRAMED but its surface variety reskins
mechanisms already present; it is not more mechanically diverse."* The "ban the obvious +
dedup + lanes" instructions produced **more exotic costumes on the same mechanisms**, not
new mechanisms — and the vivid framing then read as off-relevance to the judges.

## Conclusion — the convergence is in the model, not the prompt

Track A said "fix it structurally, not with wording." Track C shows that **structural
*prompt* edits don't fix it either** — because it's still one model generating from one
latent idea-distribution, and "be more diverse / avoid the obvious" yields reskinning, not
genuinely orthogonal mechanisms (and drifts off-relevance chasing distinctness). Persona
convergence is a property of the base model's idea distribution for a given problem.

**Therefore the effective lever is architectural, not prompt-level at all** (do NOT adopt
the Track C fix prompts):

1. **Orchestrator-level mechanism dedup after generation.** The census proves mechanisms
   are reliably machine-labelable. Run all personas, label each idea's core mechanism with
   one shared vocabulary, then drop/merge cross-persona duplicates — *outside* the
   generator, where it can actually see every persona's output (a single `generate.seed`
   call structurally cannot). This is the in-ecosystem version: a light post-generation
   pass in the orchestrator or a new `transform.dedup`-style operator.
2. **Input diversification, not voice diversification.** Convergence persists because
   every persona is handed the *same* frame. Give each generator a *different slice* —
   a different root cause, a different HMW question, a different fact — so they explore
   different regions by construction rather than by being told to differ.
3. **Stop expecting the persona axis alone to diversify.** Two personas on the same frame
   converge regardless of voice; budget for dedup or input-splitting instead of more
   persona prompt-engineering.

**Honest caveats:** n=2 frames; only a large delta is interpretable (Track A showed
substance bounces ~0.3 in noise), and here substance moved 0.0. Two levers moved together
(persona lanes/ban-obvious + the generate.seed divergence pass), so the null is the bundle.
The novelty gain (+0.75) is real but it is *framing* novelty, not mechanism novelty (the
census is what separates the two) — and it cost relevance.

---

# Track D & E — pushing on idea quality and the description workflow

After Track C, two more swings: the **architectural** idea-quality lever the evidence
pointed at (Track D), and the **description workflow** (Track E). Same discipline:
working copies, blind verdicts, adopt-only-if-it-passes.

## Track D — idea quality via input diversification (architectural) → NULL

Instead of handing every persona the same full frame, give each a **disjoint slice**
(different root causes + HMW) so they explore different regions by construction. The one
idea-quality lever not yet tested.

| Axis | Baseline | Fix (sliced) | Δ |
|---|:--:|:--:|:--:|
| Novelty | 3.25 | 3.75 | +0.5 |
| Mechanism | 4.0 | 4.0 | 0.0 |
| Relevance | 4.0 | 3.75 | −0.25 |
| **Substance** | **3.75** | **3.83** | **+0.08 (noise)** |
| **Overall distinct mechanisms /16** | **9.0** | **9.5** | **flat** |

Blind preference split (2 fix / 1 tie / 1 base). **Verdict: engaged but didn't help —
don't adopt.** Cross-persona collisions *did* drop (5→2, 4→2) — but that was the
pre-registered trap: the census caught it as convergence **relocating** inside each slice,
not disappearing — verbatim, *"the lower number reflects within-maker convergence (Maker B
used raise-switching-cost 4 of 8 times), NOT broader coverage."* Overall variety
(`distinct_all16`) stayed flat (9→9.5), and the narrower slices cost a little relevance
(same novelty↑/relevance↓ swap as Track C, milder).

**This is the third failed idea-substance intervention** (A: prompt-tune; C:
structural-prompt; D: architectural input-slice). The convergence on obvious ideas is a
property of the **base model's idea distribution for a given problem** — it does not move
to prompt wording *or* input slicing, because the model re-converges within whatever
inputs it's handed.

## Track E — description workflow (mechanism-first protocol) → MARGINAL, adopted

Rewrote the Description Writing Protocol to **mechanism-first** (concrete who-does-what in
sentence one; metaphor only as seasoning after, with a delete-the-metaphor acid test).
Isolated by holding the ideas constant: same stubs, two protocols, then a non-circular
**mechanism-recovery** test (read description alone → restate mechanism → score vs ground
truth).

| Metric | Baseline | Fix | Read |
|---|:--:|:--:|---|
| Mechanism-recovery fidelity (primary) | 5.0 | 5.0 | **tied at ceiling** |
| Clarity | 4.9 | 4.8 | tied |
| Blind pairwise clarity (10 stubs) | 3 wins | **7 wins** | fix preferred |

**Verdict: marginal positive — adopted as low-risk.** The primary (non-circular) metric
tied at ceiling, so this is **not** a measured substance win; the fix is preferred 7–3
head-to-head with zero measured downside, so the mechanism-first edit was applied to the
real `references/output-rules.md` (reversible via git) as a clear-writing improvement.

The ceiling itself is the real finding, and it's the advisor's predicted outcome: the
curated fixtures handed *both* writers a clean, pre-extracted mechanism — so even the
baseline wrote mechanism-first, and the burying failure never fully fired. In production
the burying happens because the **same** agent reasons about the idea (jargon-rich) **and**
writes it. Pre-extracting the mechanism is exactly the **two-window writer** (prior
improvement idea **#1**): a jargon-rich reasoning window that hands only the plain
mechanism to a clean writer window. My test inadvertently applied that to both arms —
which is *why* both hit ceiling. **The two-window writer is the shippable structural lever
for description quality**, not (only) protocol prose.

## The through-line (after five swings)

- **Idea substance is model-bound.** It has now resisted prompt-tuning, structural persona
  prompts, and architectural input-slicing. The only real diversity injection left is
  **out-of-model**: human ideas (record-first / *user leads*, prior idea **#8** — which is
  also the axis-2 UX gap from the first stress test) or genuinely different generators
  (model / temperature / multi-sample-then-select), **not** prompt or input rewording.
- **Concrete, verifiable things improve reliably.** Visualization (Track B, blind +0.5)
  and description clarity (Track E, 7–3) both moved. The skill's leverage is in
  *organizing, evaluating, visualizing, and persisting* ideas — and in injecting human
  ones — not in squeezing more novelty out of one model.

## Next moves

1. **Build the two-window writer** (idea #1) — the real description-quality lever; measure
   it with this harness (generate ideas → reason in a jargon-rich window → hand only the
   plain mechanism to a clean writer). This is the shippable follow-on to the protocol edit.
2. **Build record-first / user-leads** (idea #8) — the genuine idea-diversity injection
   *and* the axis-2 UX fix in one.
3. **Stop A/B-ing prompt/input tweaks for idea substance** — five swings say the ceiling is
   the model. Invest in organization, evaluation, visualization, persistence, and human
   input instead.

## Artifacts (added)

```
quality-loop/
  track-d.workflow.js + track-d-result.json   input diversification (null)
  track-e.workflow.js + track-e-result.json   description workflow (marginal, adopted)
  track-e/output-rules.base.md / .fix.md       the protocol A/B working copies
```
**Adopted to the real plugin:** the mechanism-first edit in
`plugins/ideation/skills/ideation/references/output-rules.md` (reversible via git).

---

# The lean "capture-first" default — gate + redesign

After the substance work concluded "the generation machinery doesn't earn its keep," the
natural move is to make the default **capture-first**: feed ideas from a source and store
them; if none, one plain brainstorm call; apply techniques only on demand. Two pieces:

## Gate — plain call vs the current `starter` default (blind A/B)

Does ONE plain brainstorm call (no frame / personas / techniques) lose idea quality vs
`starter` (frame + 2 personas)? Same N=16/condition, both arms on the real mechanism-first
`output-rules`, so the only variable is the generation machinery.
(`plainVsStarter.workflow.js`, `plain-vs-starter-result.json`.)

| Axis | starter (frame+2 personas) | plain (one call) | Δ |
|---|:--:|:--:|:--:|
| Novelty | 3.5 | 3.38 | −0.12 |
| Mechanism | 4.25 | 4.38 | +0.13 |
| Relevance | 3.88 | **4.5** | **+0.62** |
| **Substance** | **3.88** | **4.09** | **+0.21** |
| Distinct mechanisms /16 | 11.5 | **13** | **+1.5** |

**Blind preference: 4/4 judges preferred plain.** **Verdict: GREEN LIGHT.** The +0.21
substance delta is within the ~0.3 noise band — so the calibrated claim is *plain is
at-least-as-good, unanimously preferred, more relevant and more diverse*, not a blowout. The
bar (no quality loss from dropping the machinery) is decisively cleared.

**Attribution (the gate moved two levers — isolate them).** It compared one self-deduping
agent vs two *blind parallel* persona agents — architecture AND content varied together. The
diversity/convergence win is **architectural**: a single call can't emit cross-maker
duplicates; two blind agents collide on the obvious answers by construction (re-confirming
Track A). This validates the **single-call default** — it is NOT evidence that
technique/persona *content* is bad, and it must not be used to justify gutting the on-demand
toolkit (which runs single-context on existing ideas — a regime untested here). The one
persona-*content* effect is the relevance gap (4.5 vs 3.88): wild_card's "go wild" mandate
costs on-problem relevance. Untested: single-context + a technique vs single-context plain.

**Ship the generator that was tested.** The winning arm was a bespoke plain-brainstorm prompt;
the redesign therefore ships a dedicated `generate.brainstorm` operator (`new-default/`), NOT a
repurposed `generate.fresh` (whose frontmatter says "avoid_when: no clear hint").

## Redesign (drafted, working copy — `new-default/`)

`new-default/REDESIGN-lean-default.md` + `new-default/generate.import.md` specify the
capture-first default as exact SKILL.md edits:
- **Default = lean capture**: light frame (FK only) + one `generate.fresh` call → wall → offer
  the technique menu. No framing checkpoint, no persona fan-out, no compare report.
- **Ingest path** (the validated FEED gap): a `generate.import` operator (rides the existing
  `generate.*` emit loop → wall populates at ingest) + a planner branch + an invocation form.
- **Lazy framing**: real `frame.discover` (+ checkpoint) moves to first-deep-iterate, not
  upfront. **Techniques stay**, demoted from default to opt-in (`--techniques` / "deep" / etc.).
- **Discoverability** guardrail: every capture closes by offering the technique menu, so
  on-demand ≠ out-of-sight.
Nothing applied to the real plugin yet — these are working copies pending your go-ahead.
