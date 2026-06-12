# Liveness fix (claim-time counting + reaper) — eval results

Driver Decision 2/4 rewrite: count attempts **at claim time** (inside the atomic claim UPDATE) and
have the **reclaim path park** exhausted rows at rest (a reaper) — closing the claim→crash→reclaim
loop that error-time counting cannot see. Persona: `driver-crash-loop` in `driver-personas.js`.

## Demo-level proof first (`data-completeness-demo/liveness_demo.py`)

- **RED (error-time counting, the design the skill used to prescribe):** a row whose worker always
  crashes is claimed 12 times, `attempts` frozen at 0, still pending — and the snapshot-invariant
  audit passes **12/12** times. The starvation loop is structurally invisible to any point-in-time
  audit (a liveness hole, not a safety hole).
- **GREEN (claim-time counting + reaper):** parked at exactly N=3 claims, surfaced in dead-letter,
  every audited step passes. The GREEN trace itself surfaced a refinement now in the rule: the
  exhaustion invariant must be **lease-aware** (attempts may legitimately equal N while the Nth
  claim is in flight; the violation is an exhausted row *at rest*).
- Main demo upgraded to the new design: same partition (9/1/2), same claim sequence,
  **byte-identical `driver.view.html`** — behavior-preserving for non-crash worlds. `audit.py`
  gained the lease-aware C5 and **L1 claim-bound**, computed from the run-trace, because the
  liveness bound is only auditable against retained history (the temporal rule applied to auditing).

## Skill-level eval (runs `wf_658a46ad-78b` RED, `wf_6bb9206f-47e` GREEN)

**RED vs baseline: 5/5 median, [3,3,3,3,3] — the baseline PASSED, via generalist rescue.** All
three sims heard "spot instances", probed the vanish case, and **overrode the skill's own text** —
one recorded verbatim: *"the skill's default on-error increment was rejected because a killed
worker increments nothing."* The skill's written Decision 4 (`on error: attempts += 1`) was the
broken design; right behavior happened despite it. Same situation as the sentinel rule pre-fix
("sim-rescue at baseline"). Per that precedent, the validated delta for this persona is **text
provenance**, not behavioral pass-rate — re-rolling personas until one fails would be engineering
a RED.

**GREEN vs edited skill: 5/5 median, [3,3,3,3,3] maintained — and provenance flipped.** All three
reps report the failure design came *from* the text, nothing invented: the surfacing question
("does a worker always survive to report its failure?") is now verbatim in Decision 4; the
claim-time increment, the reaper, and the headroom sizing are quoted directly; one rep noted the
persona's exact rationalization ("the lease handles crashes") is *pre-refuted* in the 2.5
anti-rationalization table. Only parameter values (N, lease length) were generalist-supplied —
as the text intends.

**Regression (1 rep each):** `driver-poison-row` 4/4, overall 5 — notably, the sim correctly
*adapted* the kit to a lease-less single-worker case (reaper runs in the worker's own loop),
showing the rule composes rather than rigidifies. `driver-concurrent-claim` 4/4, overall 5.

**Static audit:** 4/5 with six findings, all fixed and re-verified (all six LANDED, 4/5): the
"four query shapes" count, the missing reaper in SKILL.md's driver-variant Queries list, bare
ready-predicates in the worked example's Stages table, "failure counter" wording, "(3 tries)" vs
claims, and a missing immediate-park line for terminal reported errors. The re-audit's four
worked-example residuals (funnel missing a `skipped` bucket — the same partition bug pattern fixed
in visualization.md earlier; the human-performed verdict stage's exemption from the claim kit left
implicit; "three failed claims" wording; a leaked example enum in the generic kit) were all closed.

## Verdict

The driver pattern now has no known liveness hole: the demo proves the old design's loop is real
and snapshot-invisible, the new text prescribes the fix unconditionally, sims derive the design
from the text instead of against it, adjacent personas show no regression, and the files are
internally consistent. Liveness ("every row eventually completes or parks") is now expressible as
checkable invariants: the snapshot-level reaper guarantee (no exhausted row at rest) plus the
trace-level claim bound (no (row, stage) claimed more than N times).
