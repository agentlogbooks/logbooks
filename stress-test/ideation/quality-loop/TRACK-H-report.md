# Track H — why developing works but the technique doesn't

## Verdict (with more power now)

Track G's n=2 finding held up — and hardened — at 4 frames.

**Technique choice is noise (and if anything, a slight tax).** Across the blind A/B tally, the named techniques won **3 of 12** cells against plain-develop and lost 9. None of them beat plain on average quality:

| technique | wins | losses | avg tech_q | avg plain_q |
|---|---|---|---|---|
| reverse | 2 | 2 | 13.5 | 13.75 |
| scamper | 1 | 3 | 12.75 | 14.0 |
| sixhats | 0 | 4 | 12.25 | 14.75 |

Plain out-scores every technique on its own arm, and the only frame where any technique won twice (reverse) it still tied plain on average. Six Hats went 0/4. Whatever lift a technique seemed to give at n=2 was within the noise; with 4 fresh frames it disappears entirely.

**Developing beats raw — cleanly, 4 for 4.** On the lift test (a developed idea vs. a fresh raw idea for the same goal), the developed idea won every frame:

| frame | dev_q | raw_q |
|---|---|---|
| cafe | 15 | 11 |
| b2b | 15 | 12 |
| library | 15 | 10 |
| cupwaste | 15 | 12 |

Every developed idea hit a ceiling-grazing 15; raw landed 10–12. That is the real, repeatable signal.

## The "why" — the new part

The blind tally tells us *that* the technique doesn't help. The three instruments tell us *why*.

**1. Move-tagging: plain already makes the moves.** Tagging each develop by the kind of improvement-move it made shows the techniques aren't doing anything plain isn't. `RISK` (hardening against failure) is the single highest-frequency move overall — top move in plain, reverse, and sixhats — yet it isn't a technique-exclusive trick: plain reaches for it as readily as the lenses do. The move that appears in *every* arm, including plain, is `ENF` (make the idea actually bite / recur / stick), with `TIME` the other universal. No technique unlocked a move-type plain lacked; they mostly reshuffled the *mix* (scamper leaned `SUB`, reverse leaned `SCOPE`) while landing the same kind of deepening.

**2. Same-fix convergence: the obvious fix is seed-determined, not lens-determined.** On **42%** of seeds (5 of 12), all four methods converged on the *same core fix*. And these aren't vague overlaps — they're near-verbatim:
- *cafe*: all four harden the baker deal into two protected revenue lines (fixed rent + consignment cut, fenced by a written agreement and a hard out-by-time). "Scamper's weekly rotation is the same mechanism amplified, not a new one."
- *library*: all four arms land "near-verbatim" on a fixed-time recurring weekly draw plus an acoustically-zoned quiet area.
- *cupwaste*: across seeds, all arms converge on turning the per-cup fee into a running personal tally, and on killing the $5 deposit friction with a one-tap pre-auth.

When a seed has one glaring weak point, every method finds it. The fix lives in the seed, not the lens.

**3. Divergence-from-plain: technique output ≈ plain output.** Scoring how far each technique's output drifted from plain, "different *and better*" shows up in only **2 of 12** cells — both scamper. Everything else is `nearly_identical`, `minor_variation`, or `different_but_not_better`. Where the techniques did diverge, they usually diverged sideways (different, not better) or drifted into a "common attractor" by losing the seed's identity (cupwaste seed 3) — divergence-by-loss, not divergence-by-improvement.

**Conclusion.** The lens doesn't help because (a) the model already makes the improvement-moves the techniques are supposed to inject; (b) the highest-value fix is determined by the seed's dominant flaw, so all roads lead to it; and (c) the technique's output therefore ends up essentially the same artifact as plain — just reached by a different route, occasionally a worse one.

## What developing actually does

Developing takes a raw idea and makes its already-stated promise *bite*: the dominant work is `ENF`/`RISK` — converting a vague mechanism into something enforceable, habit-forming, and failure-hardened. That is exactly the gap between raw (10–12) and developed (15).

Two real before→after pairs:

**cafe — "Morning receipt prints an afternoon reward."**
- *raw*: "Every 7-11am receipt prints a same-day 2-5pm coupon… 'free cookie with any drink after 2 today.'"
- *developed*: "The reward is bundled to a paid purchase, not given away, so each redemption is a net-new afternoon trip with a sale attached… the footer also stamps a tiny 'afternoon streak' line — redeem three afternoons in a week, the fourth drink is free — so regulars build a return reflex."
- *what changed*: tied the reward to a paid afternoon purchase and added a multi-day streak, so it generates incremental sales and a return habit instead of giving margin to people who'd come anyway.

**cupwaste — "The Cup Is on the Receipt."**
- *raw*: "a $0.35 'cup' line prints under the latte; order in your own tumbler and the screen has already knocked $0.35 off."
- *developed*: "the receipt… leads with the saving plus a running tally: 'cup $0.00 — you've kept $9.60 this month, 24 cups avoided'… the district steps it up on a published schedule (40 cents this year, 60 next)… so the felt cost is a growing personal number rather than an ignorable per-cup pittance."
- *what changed*: surfaced each customer's running monthly total and a published rising rate, so the surcharge actually bites.

In both, the seed's idea survives intact; developing makes it *work*.

## What it means for the skill

**Plain-develop is enough.** "Just improve it" reaches the same high-quality fix the structured techniques reach, more reliably and without the occasional sideways drift. The techniques (SCAMPER, Reverse, Six Hats) should stay as **optional flavor** — a way to vary the route or the framing — not as a quality lever, and never as a default the user must pick through.

This fits the larger pattern. Idea **generation** is model-bound: six prior nulls show prompt/technique tuning doesn't lift what the model produces from cold. But **developing a user-chosen idea is a real lever** — 4/4 lift, every developed idea at ceiling. The skill's value is concentrated in the develop step, and that step needs no technique scaffolding to deliver it.

## Caveats

- 4 frames, 3 seeds each, **single sample per cell** — no within-cell variance estimate.
- The blind A/B tally is the verdict; the move-tagging, convergence, and divergence numbers are **interpretive** instruments layered on top to explain it, not independent confirmations.
- 12 A/B cells is more power than Track G's n=2 but still small; "technique = noise" is a failure-to-find-a-difference, not a proof of exact equivalence.
- The "why" rests partly on a single judge's tagging of move-types and same-fix convergence, which is inherently subjective.