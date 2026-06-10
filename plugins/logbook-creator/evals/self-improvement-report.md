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

## Re-running

```
Workflow({ scriptPath: "plugins/logbook-creator/evals/self-improve.workflow.js" })
```

Edit `PERSONAS` to change the scenario matrix; edit `SKILL_PATH` to target a different skill.
