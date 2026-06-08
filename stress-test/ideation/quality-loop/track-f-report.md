# Track F — classical techniques vs the plain default

## Verdict

**No technique beats the plain single-call default on blind substance.** Across all three —
Reverse Brainstorming, SCAMPER, Six Thinking Hats — the honest call is **ties or losses**,
never a clean win.

| Technique | Blind tally vs plain (2 frames × 2 orders) | Avg substance Δ | Honest call |
|---|---|---|---|
| Reverse | **1 tech / 3 plain** | +0.00 | **loses the tally, ties on substance** |
| SCAMPER | 2 tech / 2 plain | −0.50 | **ties (2-2), entirely frame-split** |
| Six Hats | 2 tech / 2 plain | −0.25 | **ties (wash), diversity inflated by off-goal levers** |
| **Overall** | **4 tech / 7 plain** | — | **plain is at-least-as-good against all three** |

The reason it's a wash and not a signal: **the deltas invert across frames.** SCAMPER sweeps
the cafe blind tally 2-0 (+1.0 substance) and is then swept 0-2 on b2b (−2.0). Reverse is
+0.5 on cafe, −0.5 on b2b. Six Hats is −0.5 / +0.0. With only **n=2 frames**, a sign that
flips between them is not a small effect — it is the definition of no frame-invariant signal,
which is exactly what noise looks like. (These 11–14 numbers are batch-aggregate sums over 16
ideas, not the project's 1–5 per-idea scale, so the ~0.3 per-idea noise band is a reference,
not a mechanical cutoff — but for the genuinely tiny averages, Reverse 0.0 and Six Hats −0.25
sit comfortably inside it.) The position-swapped pairs say the same thing from the other
direction: the only *order-consistent* signals lean **plain** (Reverse b2b 0-2, SCAMPER b2b
0-2), the lone tech sweep (SCAMPER cafe) is frame-local, and Six Hats is 1-1/1-1 — pure order
noise both frames.

And the census confirms these are **in-model reshuffles, not diversity injections**: PLAIN is
the **most mechanically diverse arm in BOTH frames** (15/16 distinct each time). Every
technique scores *equal or lower* on problem-relevant distinct mechanisms. Each one trades
diversity or relevance for a characteristic bias — they relocate convergence rather than
escape it, the same pattern Tracks A/C/D found. **Substance is still model-bound.**

---

## Per-technique

### Reverse Brainstorming

- **Blind tally:** 1 tech win / 3 plain wins. Loses outright. Its only order-consistent
  signal (b2b, both orders, 0-2) favors **plain**.
- **Substance:** cafe 13.5 vs 13.0 (+0.5), b2b 13.5 vs 14.0 (−0.5) → **+0.0 average.** Dead
  even, sign-flipped.
- **Census diversity:** the **least diverse structured arm** — 13/16 distinct, tied with Six
  Hats and below plain's 15 and SCAMPER's 14. Its signature is a **3× collapse onto paid
  workspace (M1)**: #4 monthly desk pass, #5 reconfigure floor for lingering, #15 seat +
  bottomless. It does contribute one robust unique (M18, the "1:45pm SMS push") and shares
  M17 (waste-repurpose) with SCAMPER, but the headline is convergence, not coverage.
- **Real ideas:**
  - *"Morning receipt unlocks an afternoon return — Print a same-day coupon on every 7-11am
    receipt that's only redeemable 2-5pm that same day… 'bring this back today 2-5pm for a $2
    cookie + drip refill.'"*
  - *"A 3pm fresh bake people can smell — Fire the idle ovens for a single small batch that
    comes out hot at exactly 3pm daily… warm cinnamon rolls or savory scones pulled at 3:00
    and announced on the sidewalk board."*
  - *"Each member gets their own front door — When a schedule publishes, every team member
    receives a personal link showing only their own upcoming shifts and lets them tap to
    confirm or request a swap."*
- **Signature failure:** **converges within itself.** Despite the "invert the problem" framing,
  it piles three of sixteen ideas onto the single workspace lever — its inversion engine keeps
  arriving at the same attractor plain reaches once.

### SCAMPER

- **Blind tally:** 2 tech / 2 plain — but a clean **frame split**, not a wash of mixed close
  calls. It **swept cafe 2-0** and was **swept b2b 0-2.** Order-consistent within each frame,
  opposite across them.
- **Substance:** cafe 12.5 vs 11.5 (**+1.0**), b2b 11.0 vs 13.0 (**−2.0**) → **−0.5 average**,
  the largest negative of the three, driven entirely by the b2b crater.
- **Census diversity:** the **least-collapsing technique** — 14/16 distinct in both frames,
  max-repeat 2, no 3× pile-up (the only structured arm as flat as plain). It contributes a
  distinct cluster of operational singletons on b2b (M6/M12/M13/M22: payroll wiring, availability
  board, etc.). **Important:** this is "collapses least," **not** "more diverse than plain" —
  plain still leads 15 to 14 in both frames. And SCAMPER's distinctive operational singletons
  land in **exactly the frame (b2b) where it lost 0-2 and dropped −2.0 on substance.**
- **Real ideas:**
  - *"Guest-Baker Residency — Hand the afternoon counter to a rotating local baker or dessert
    maker who sells their own goods from the cafe and shares revenue… a neighborhood pastry
    chef takes over Tuesday afternoons selling laminated croissants under their own name."*
  - *"Hot-From-The-Oven Savory Hour — Fire the idle afternoon ovens for warm savory items the
    morning menu never carries… cheese-and-herb scones and personal flatbreads come out fresh
    at 2:30 and 3:30 daily."*
  - *"Wire the schedule straight into payroll — connect published schedules to the team's
    payroll or timesheet system so approved hours flow automatically into the next pay run."*
- **Signature failure:** **frame volatility + a novelty-for-relevance reshuffle.** SCAMPER's
  Substitute/Combine/Other-uses prompts generate the most *distinct* moves, but on b2b those
  distinct moves drift toward **feature-expansion and lock-in** (payroll wiring, availability
  board, payroll as "source that feeds paychecks") — stickiness adjacent to the goal rather
  than attacking the actual root cause of early churn (admins never reaching the first-week
  aha). It bought distinctness and paid in relevance, then lost the blind judgment 0-2. This
  is the cleanest in-sample demonstration of the prior tracks' reshuffle pattern.

### Six Thinking Hats

- **Blind tally:** 2 tech / 2 plain — a genuine **wash** (1-1 on each frame, both orders). No
  order-consistent signal in either direction.
- **Substance:** cafe 12.5 vs 13.0 (−0.5), b2b 12.5 vs 12.5 (+0.0) → **−0.25 average**, inside
  the noise band.
- **Census diversity:** 13/16 distinct on paper — **but inflated.** The census explicitly
  flags that the raw 13 includes **off-goal guardrail/process levers** and estimates it would
  drop to **~9-10 once those are excluded**, making plain's lead in *problem-relevant* diversity
  wider than the raw counts show. Its signature is a **3× collapse onto operational guardrails
  (M19)** on cafe — cannibalization wall, spend cap, staggered shift — none of which grow
  revenue; and **M20 ×3** on b2b. The "Black Hat" (risk/critique) lens manufactures these.
- **Real ideas:**
  - *"Set afternoon prices from the real cost of an idle seat — The owner calculates that an
    empty 2-5pm table earns nothing and prices a fixed 'afternoon set' (drink plus snack) at a
    margin that beats zero… a $6 coffee-and-cookie set is offered 2-5pm because even thin
    margin on a previously empty chair is pure upside."*
  - *"A quiet, slow corner marketed as the city's calmest 3pm — leans into the empty room by
    branding the afternoon as a deliberately unhurried, low-noise refuge… a chalkboard reads
    'nobody rushing you here from 2-5 — stay as long as you like.'"*
  - *"At-Risk Radar From Login And Scheduling Signals — A background job scores each new account
    daily on whether it has published a full week and whether more than one person has logged
    in, and flags accounts trending toward the silent-then-cancel pattern."*
- **Signature failure:** **drifts off-goal.** The hat rotation spends three of sixteen slots on
  cost-control / risk-mitigation levers (guard against cannibalization, cap spend) that answer
  "what could go wrong" rather than the actual goal (grow revenue / cut churn). Its diversity is
  partly an artifact of generating ideas that aren't on-topic.

---

## What it means for the skill

**The capture-first decision is unchanged.** Plain stays the default; techniques stay opt-in —
and Track F gives no reason to move any of them in either direction:

- **No promotion.** No technique consistently beats plain on substance, lifts problem-relevant
  diversity above plain, or improves relevance. The only sizable substance moves (SCAMPER ±1.0/−2.0)
  cancel and frame-flip. There is nothing here that would justify wiring a technique into the
  default path.
- **No gutting either — and this is a scope limit, not an endorsement.** Track F tested
  techniques as single-context **generators** (each "produced 16 ideas" from the frame). The
  shipped opt-in toolkit uses these same techniques as **transforms on already-captured ideas**
  — a different operation that **Track F did not test.** A technique can be a poor cold-start
  generator and still be a useful "take these 5 ideas and SCAMPER them" lens. So Track F neither
  promotes a technique to default nor argues for removing the opt-in toolkit; the on-demand
  menu stays as is, untouched by this evidence.

**Tie-back to "substance is model-bound."** This is the answer to Track F's open question:
single-context **plain vs single-context technique**, architecture and sample size held
constant. The techniques are **in-model rewords, not out-of-model diversity injections.** Each
re-derives the same convergent gravity wells the census found shared across all four arms
(paid workspace, morning-receipt trigger, afternoon-product reframe, hosted events, quantify
time-saved, human-builds-week), then adds a **characteristic bias** of its own — Reverse →
workspace convergence, Six Hats → off-goal drift, SCAMPER → frame volatility / relevance loss.
A different prompt structure on the same model moves the *shape* of the convergence, not the
*amount* of real novelty. **Substance has now resisted a sixth swing** (Tracks A, C, D, and now
three classical techniques). The only diversity that pays remains genuinely out-of-model: human
ideas (capture-first), or genuinely different generators (model / temperature / multi-sample-
then-select) — never another in-model reword.

---

## Caveats

- **n=2 frames** (cafe weekday-afternoon revenue; b2b SaaS early churn). Two points cannot
  separate a frame effect from a technique effect — which is precisely why the **frame-inverting**
  deltas read as noise rather than a small real effect.
- **Single sample per arm.** One 16-idea batch per (frame × technique). No within-arm variance
  estimate; a re-roll could move any single cell.
- **The blind A/B is the verdict.** Position-swapped, de-anonymized substance comparison is the
  primary signal: plain at-least-as-good against all three.
- **The census is a diagnostic, not the verdict.** "Most diverse" / "off-goal" / "collapses
  least" explain *why* the blind result came out as it did and surface each technique's
  signature bias — they don't override the head-to-head judgment.
- **Generators only.** Techniques-as-transforms (the shipped opt-in flow) remain untested here.