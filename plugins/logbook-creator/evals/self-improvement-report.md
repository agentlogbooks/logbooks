# logbook-creator — self-evaluation & improvement run

**Run:** `wf_91ee9671` · 84 agents · ~2.25M tokens · ~35 min · 5 rounds
**Harness:** `self-improve.workflow.js` (re-runnable)

## What ran

A closed-loop **evaluate → diagnose → improve → re-evaluate** cycle, hill-climbing for 5 rounds with a regression guard (accept an edit only if the aggregate score does not drop).

Each evaluation pass = **6 hidden-state personas** + **1 static consistency audit**:

| Persona | Tests |
|---|---|
| crisp-expert-single | happy path + question fatigue (no over-interrogation) |
| vague-novice | the Step 2.3 usage-commitment gate (push back / redirect / trial) |
| ephemeral-path | double ephemeral-path rejection (2.1 + Step 5) |
| hidden-tracker-refuse | redirect a Jira-shaped need away from a logbook |
| multi-entity-power | multi-entity design + identity layers + SQLite/JSONL |
| hidden-logbook-prose | detect a logbook hiding behind "a doc" |

Personas reveal facts only when asked, so the run tests elicitation order and gating, not just outputs. Each transcript is graded by an **independent judge** (separate agent, blind to the skill) against a fixed behavioral contract. Aggregate score = `0.8 × mean(persona overall) + 0.2 × static consistency`, on a 0–5 scale.

## Scorecard

| | Score |
|---|---|
| Baseline | **3.97 / 5** |
| Final (best) | **4.09 / 5** |
| Δ | +0.13 (within eval noise — see below) |
| Fixes proposed | 5 |
| Fixes accepted by guard | 1 |

Final per-persona overall (all contracts passed): crisp-expert 4.5, vague-novice 4.0, ephemeral-path 4.5, hidden-tracker 4.7, multi-entity 4.0, hidden-logbook 4.5.

## Round-by-round

| R | Proposed fix | Sev | Re-eval | Guard | Disposition |
|---|---|---|---|---|---|
| 1 | "three sub-questions" → four (Step 2 intro miscount) | high | 3.86 | reject | **Applied deliberately** (corroborated) |
| 2 | Query-quality checklist (ban positional awk / enum sorts) | high | 3.63 | reject | Deferred — needs new template subsection |
| 3 | Step 5 writability check fails when parent dir missing | high | 3.79 | reject | **Applied deliberately** (corroborated) |
| 4 | Introduce pending-auth binding concept in Step 4 | high | 3.77 | reject | **Deferred to human** (feature-direction call) |
| 5 | Standardize local-override filename (Step 5 vs Anti-patterns) | med | 4.09 | **accept** | **Applied** (loop's decision) |

## The key finding: the eval is too noisy for a strict regression guard

Four of five candidates scored **below** baseline on re-evaluation even though each fixed a genuine high-severity bug — including bugs the static audit *itself* flagged. A strictly-not-worse skill version scoring 0.2–0.3 lower is sampling noise from the stochastic persona simulations, not real regression. So the guard rejected good fixes, and the +0.13 "win" is itself inside that noise band.

**Implication for the methodology:** the loop's *diagnosis* is the valuable output; its single-sample accept/reject signal is not trustworthy. Fixes to make it sound:
- **N-of-M re-eval**: run each candidate eval 3–5× and compare distributions (or medians), not single samples.
- **Paired/A-B grading**: one judge sees baseline + candidate transcripts for the same persona seed and picks the better — paired comparison cancels per-seed noise.
- **Deterministic gate first**: gate on the static-audit + artifact-lint (near-deterministic) and use persona scores only as a secondary, noise-aware signal.

## Harness bug found & fixed

The default workflow subagent has `Edit`/`Write`, so diagnose agents wrote three candidate edits **directly to the real SKILL.md** despite an explicit "do not edit files" instruction — mixing accepted and rejected changes on disk. Fixed in the checked-in harness by setting `agentType: 'Explore'` (read-only) on every agent. The skill file was reset and the deliberate fix-set re-applied cleanly.

## Applied to SKILL.md (this branch)

1. **Step 2 intro count** "three sub-questions" → "four … (2.1–2.4 below)" — *prevents skipping Step 2.4.*
2. **Step 2.3 flow** "Proceed to Step 3" → "Proceed to Step 2.4 (… do not skip it)" — *the actual mechanism by which 2.4 was being skipped.*
3. **Step 5 writability** — ancestor-walking test + explicit `mkdir -p` — *no longer false-fails on the skill's own recommended `~/.local/state/<name>/` defaults.*
4. **Local-override filename** — Anti-patterns now points to Step 5's canonical `<name>.logbook.local.yaml` instead of an undocumented path. *(loop's one accepted fix.)*

## Left for the human owner (not applied autonomously)

- **Dangling `bindings` feature — wire-in vs remove.** Round 4 wired the concept into Step 4, but the spec template still has no `## Bindings` section, so the wiring stays incomplete (Step 5 references "the bindings section" that doesn't exist in the template). Decide the direction, then make it coherent end-to-end. This is the highest-value remaining item.
- **Query-snippet quality** — emit named-column access (python `csv.DictReader` / `mlr`) over fragile positional `awk $5`; field-scoped tag filters over bare `grep`; explicit enum rank ordering over alphabetical sorts.
- **Version mismatch (cross-file, out of loop scope)** — `plugin.json` = 2.0.0 vs `marketplace.json` = 1.1.0 (and ideation 2.2.0 vs 2.3.0). Pick the canonical version and sync.
- **Step 2.4 short-circuit** — add an explicit "confirm answers already given in Step 1 rather than re-asking" clause to cut question fatigue for the crisp-expert case.

## Run 2 — noise-aware median guard (`wf_db60e4d2`, 266 agents, 8.3M tok, ~84 min)

The fix to the methodology: evaluate every version **K times** and compare **medians**, after first calibrating the noise band. (Caveat: `args` was passed as a JSON string, so `skillPath` fell back to the default — run 2 evaluated the **already-fixed** skill, not the original. The K-values matched the defaults, so they were unaffected.)

**Noise band — the headline.** Five identical evals of the unchanged skill scored `[4.01, 3.91, 3.87, 3.87, 4.15]` → **median 3.91, sd 0.12, range 0.28**. This is hard confirmation that run 1's single-sample verdicts (a +0.13 "win" and 0.11–0.34 "regressions") were **noise** — the noise floor alone is 0.28. Per-persona, the noise is concentrated: **crisp-expert-single** swings `[4, 3, 3, 3.5, 3]` (sd 0.45, range 1.0); the other five are tight (sd 0.13–0.29).

**Guard result: 3 accepted vs 1.** median 3.91 → 4.14.

| R | Fix | Δ median | Samples | Verdict |
|---|---|---|---|---|
| 1 | Add YAML frontmatter block to spec template (wires in `bindings`) | **+0.20** | [4.11, 4.17, 3.87] | accept — **above noise** |
| 2 | Step 2 intro topics (v1) | −0.21 | [3.89, 3.83, 4.07] | reject |
| 3 | "who owns it" → "how entries are partitioned" | +0.01 | [4.11, 3.95, 4.12] | accept — within noise |
| 4 | Intro: conditional third artifact | +0.03 | [4.09, 4.24, 4.14] | accept — within noise |
| 5 | Step 5 heading artifact count | −0.24 | [3.9, 4.13, 3.83] | reject |

**Honest caveat:** only **R1 (+0.20)** is unambiguously above the noise band. R3 and R4 cleared only via the `>=` tie and median-of-3's residual noise (~0.1) — they should be judged on merits, not score. So median-of-3 *materially* improves the guard (kills the gross false-rejections) but does **not** make sub-0.1 deltas trustworthy. To accept fine-grained fixes you need higher K, or — better — fix the noise at its source: tighten the **crisp-expert** persona's judging (it alone contributes most of the variance).

**Applied from run 2:** R3 only — it corrects an inaccuracy *my own* run-1 fix introduced ("who owns it" is not a sub-step; 2.2 is partitioning). The loop caught my mistake.

**Evidence for the deferred decision:** R1 wiring in `bindings` scored a clear **+0.20**, so the data favors *wiring in* over removing. Not auto-applied because (a) it's the design call left to the owner and (b) the static audit in the same run flagged the loop's specific implementation (an always-present frontmatter fence) as a *new* contradiction — the clean form is a conditional "if cloud backend, prepend this frontmatter" note plus a coherent artifact-count update across the intro and the Step 5 heading.

## Re-running

```
Workflow({ scriptPath: "plugins/logbook-creator/evals/self-improve.workflow.js",
           args: { skillPath: "/abs/path/SKILL.md", kBase: 5, kCand: 3, rounds: 5 } })
```

Pass `args` as a real object (not a JSON string). Edit `PERSONAS` to change the scenario matrix.

## Driver-pattern extension — RED baseline (`wf_aeea6414-240`, 51 agents, 1.57M tok, ~47 min)

A new capability under evaluation: **driver (work-queue) logbooks** — the schema is a state machine and an
empty stage cell is the trigger for an agent to do that stage (`WHERE reviewed IS NULL` = the work queue).
Five new hidden-state personas (`evals/driver-pattern/driver-personas.js`), one per footgun, graded with an
added `DRIVER_GROUND_TRUTH` block. Worked example + design fixtures in `evals/driver-pattern/`. This is the
**before** snapshot, run against the unchanged skill (which has no driver branch).

**Headline: mean overall 2.5/5 · contract items 58/105 (55%).**

| Persona (footgun) | Contract | Overall median | Read |
|---|---|---|---|
| driver-poison-row | **0/20** | 1.0 (lows 0.5) | total miss — no attempts/parked concept |
| driver-stage-dag | **0/20** | 1.0 | total miss — no DAG/prerequisite concept |
| driver-sentinel-trap | 24/25 | 3.0 (artifact lens 2) | **emergent pass, not skill coverage** (see below) |
| driver-concurrent-claim | 16/20 | 3.5 | sees the race 5/5, emits the lease only 3/5 |
| driver-vs-tracker | 18/20 | 4.0 | existing tracker guard holds (1 run fooled by veneer) |

**Key finding — the two numbers disagree, and that is the signal.** 55% contract-pass *overstates* coverage.
`driver-sentinel-trap` passed 24/25 yet every judge's gap list says *"SKILL.md has no mechanism to elicit the
sentinel trap"* and one finding is titled *"correct behavior was emergent, not instructed."* A capable Sonnet
probed and built a status sentinel from its own competence — **sim-rescue**, not skill coverage (corroborated
by artifact lens stuck at 2, and `concurrent-claim` recognizing the race 5/5 but emitting the mechanism only
3/5). The trustworthy signal is the floor, not the average: **DAG and poison are a hard 0/20** (instructed-
absence the model can't rescue); sentinel/claim are fragile-emergent; only the tracker guard is genuinely
covered. This mirrors the run-1/run-2 lesson from the other direction: behavioral sims are *optimistic* about
capabilities the skill doesn't contain — trust the gap/static signal over the behavioral average.

**Fix (all 12 high-severity gaps converged on it): a named driver branch.** Priority by leverage:
poison-row (0/20) → stage-DAG (0/20) → claim/lease mechanism (3/5) → make the sentinel gate forced not
emergent → preserve the tracker guard. Implemented next as generic rules with an anti-rationalization table
to force the flow; re-run will measure the green delta vs. this baseline.

## Driver-pattern extension — GREEN re-eval (`wf_ba42f8c1-391`, 51 agents, 1.71M tok, ~18 min)

Same rig (same 5 personas × K=5, identical prompts), against the patched skill — apples-to-apples. The
branch: a 6th motivation in Step 1, **Step 2.5** (gate + anti-rationalization table + five required
decisions), a sentinel carve-out in 3B, stage-column kit in 3C, storage override in Step 4, a Driver-
variant spec section, four anti-patterns, and `references/work-queue.md`.

**Headline: mean overall 2.5 → 4.36 (+1.86) · contract 55% → 94% (58→99/105) · fully-failed 2 → 0.**

| Persona | RED contract | GREEN contract | RED overall | GREEN overall |
|---|---|---|---|---|
| poison-row | 0/20 | **20/20** | 1.0 | 4.5 |
| stage-dag | 0/20 | **19/20** | 1.0 | 4.0 |
| concurrent-claim | 16/20 | 20/20 | 3.5 | 4.5 |
| sentinel-trap | 24/25 (emergent) | 20/25 (instructed) | 3.0 | 4.8 |
| vs-tracker | 18/20 | 20/20 | 4.0 | 4.0 |

The two hard 0/20 capability holes (poison, DAG) closed. The tracker guard *strengthened* (redirect 4/5
→ 5/5, no veneer fooling). concurrent-claim lease mechanism 3/5 → 5/5. Sentinel is now instructed not
sim-rescued (artifact lens 2 → 5). The anti-rationalization table converted fragile emergent behavior
into forced behavior — that is why the floor rose.

**Remaining (now refinements, not holes).** Judges flagged: (1) Decision 1's sentinel reads as
*conditional* on the user's "no" — one rep accepted "no" without an adversarial probe (the lone overall-2
outlier; sentinel contract 20/25). Make the sentinel **structural/unconditional**. (2) A numbering
collision I introduced — the anti-rationalization table labelled the tracker row "(Decision 5)" while the
numbered Decision 5 is *terminal outcomes*. (3) No explicit stop-redirect when the tracker gate fires
mid-2.5. Plus artifact nits: emit one atomic-claim per stage; `CREATE INDEX` in the driver template;
probe for an implicit DAG even when one stage is visible; the SQLite `NULL != value` caveat. Applied in a
tightening pass; a confirmation re-run measures it.

## Driver-pattern extension — CONFIRM re-eval + convergence (`wf_85d63f30-0ab`, 51 agents, 1.70M tok, ~17 min)

Same rig a third time, against the tightened skill (unconditional sentinel; numbering-collision fix;
pre-check stop-redirect; implicit-DAG probe; per-stage atomic claim + `CREATE INDEX`; SQLite `NULL`
caveat in `work-queue.md`).

**Headline: mean overall 4.36 → 4.46 · contract 94% → 89% (99→93/105) · fully-failed still 0.**

| Persona | GREEN | CONFIRM | note |
|---|---|---|---|
| sentinel | 4.8 / 20/25 | 4.8 / **25/25** | unconditional-sentinel fix landed — perfect, no outlier |
| vs-tracker | 4.0 / 20 | 4.5 / 20 | guard solid, slightly up |
| concurrent | 4.5 / 20 | 4.5 / 16 | one outlier rep (built-single) |
| dag | 4.0 / 19 | 4.5 / 16 | one outlier rep; **median up** |
| poison | 4.5 / 20 | 4.0 / 16 | one outlier rep |

**The contract dip is rep-noise, and the median metric proves it.** Targeted fix worked (sentinel
20/25 → 25/25). Mean overall *rose*; per-persona medians flat-or-up (dag 4.0 → 4.5). The 94→89 drop is
three single-rep outliers where the sim didn't engage the driver gate in 1 of 5 reps (one returned
`built-single`) — whole-rep stochastic misses, **not** the "accepted a dismissive answer" mode (per-item
passes were a uniform 4/5). Aggregate delta +0.10 is inside the established ±0.28 band.

**Convergence — loop stopped.** Three rounds: **2.5 → 4.36 → 4.46.** Both 0/20 capability holes closed,
sentinel perfected, tracker guard solid + strengthened (redirect 4/5 → 5/5 over the runs), zero
fully-failed personas. Green→confirm deltas are within noise; a 4th round would surface a different random
outlier set. ~5.0M tokens across the 3 rounds (153 sim+judge agents).

**Recommended (optional) next refinements — proven pattern, apply-and-measure.** The judges converged on
extending the Decision-1 counter-probe device (which demonstrably took sentinel to 25/25) to Decisions 2–4:
challenge a dismissive "they're independent" / "every item completes" once with a concrete counter-example
before accepting. Also: make `<stage>_attempts` + a `failed` status **unconditional** schema defaults (the
failure question sets `N`, not whether to include them); and add a Step 5 check that every status literal
used in a query appears in the Stages table + CHECK constraint. These harden against an *actively
dismissive* user (not the noise above), so they should be applied **and re-measured** in a future round
rather than shipped unmeasured — consistent with the loop discipline.
