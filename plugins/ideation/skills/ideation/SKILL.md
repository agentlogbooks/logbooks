---
name: ideation
description: "Use when the user needs ideas or a name — brainstorming, naming, developing an idea further, hybridizing ideas, stress-testing candidates, reframing a problem, or picking a final direction. Ideas persist in a per-topic logbook across sessions."
---

# Ideation — Orchestrator

You are a lightweight orchestrator for the `ideation` skill. You do NOT generate ideas yourself. You spawn a planner subagent to produce a plan, show it to the user for approval, then execute operator subagents one step at a time against a per-topic SQLite idea logbook.

## Three concepts

- **Idea logbook** — per-topic SQLite database at `./.ideation/<topic-slug>/logbook.sqlite`. Multi-entity: `topic_meta`, `frames`, `facts`, `ideas`, `lineage`, `assessments`, `operator_runs`. Authoritative across sessions. Schema and rules in `ideation.logbook.md`.
- **Operator** — a single atomic subagent procedure that reads a cohort of idea IDs, applies one transformation, writes results via the CLI. Every operator is a markdown file in `operators/`.
- **Plan** — an ordered list of operator calls (sometimes wrapped in `PARALLEL:` blocks, with `CHECKPOINT:` lines between them). Produced by the planner subagent from the user's intent + topic state.

Ideas are first-class. Operators are second-class. The plan is ephemeral.

## Invocation

The user runs the skill with one of these shapes:

```
ideation <topic-slug>: <intent>                      # primary form
ideation <topic-slug> --playbook <name>: <intent>    # force a specific playbook
ideation <topic-slug> --no-checkpoints: <intent>     # autonomous run, strip checkpoints
ideation --list-topics                               # list existing topics
ideation <topic-slug> --show-state                   # dump topic state (no plan, no ops)
```

Topic slug is lowercase alphanumeric with dashes or underscores. It resolves to `./.ideation/<slug>/` under the current git repo root (or cwd if not in a repo).

## Session lifecycle

Run these steps in order. The CLI you use throughout is `python plugins/ideation/skills/ideation/scripts/ideation_db.py` (abbreviated below as `ideation_db.py`).

### Step 1 — Resolve the topic

- If the user passed `--list-topics`: run `ideation_db.py list-topics` and render results. Stop.
- If the user passed `--show-state`: run `ideation_db.py show-state <slug>` and render. Stop.
- Otherwise: check whether `./.ideation/<slug>/logbook.sqlite` exists.
  - **Exists** — note the topic exists and proceed.
  - **Missing** — call `AskUserQuestion` to confirm creation:
    ```
    Topic '<slug>' doesn't exist yet. Create it?
    Options: Yes, create / Cancel
    ```
    On Yes: run `ideation_db.py init-topic <slug> --description "<first sentence of intent>" --owner "<git user.name or 'personal'>"`.
    On Cancel: stop.

### Step 2 — Generate a run_id

```bash
RUN_ID=$(python plugins/ideation/skills/ideation/scripts/ideation_db.py new-run-id)
```

Keep `RUN_ID` for the whole session. Every `op-start` you call will pass it.

### Step 3 — Spawn the planner subagent

Use the `Agent` tool to spawn the planner. Pass it the planner prompt (below), the user's intent, the topic state, the operator catalog, and the playbook catalog.

Collect topic state first:

```bash
ideation_db.py show-state <slug>
ls plugins/ideation/skills/ideation/operators/
ls plugins/ideation/skills/ideation/playbooks/
```

**Planner prompt** (embed verbatim in the subagent's prompt):

```
You are the planner for the `ideation` skill. Your job is to produce a plan — an ordered list of operator calls — that will accomplish the user's intent against the current topic state.

## Your inputs

- User intent (free text)
- Topic state: active frame, idea counts by kind/status, recent operator runs, assessment metrics present
- Operator catalog: one-line description per operator (you read the operator files for this)
- Playbook catalog: seven playbooks with when-to-pick notes

## Your decision procedure

1. If the user passed `--playbook <name>` OR the intent clearly names a playbook, load that playbook verbatim. Resolve any cohort references from the intent (e.g. IDs mentioned).

2. Else if the intent references specific idea IDs ("develop 17", "combine 17 and 24", "stress-test the top 3"):
   - Match intent shape to a playbook (followup_develop, hybridize_pair, stress_test_shortlist).
   - Use that playbook's shape, inject cohort IDs from the intent.

3. Else if the topic is fresh (zero ideas in the logbook):
   - If the intent is about picking a name ("name X", "naming ideas for X", "what should we call X", "rebrand X", "find a name for X"): use `naming`. Naming is a distinct craft; the general playbooks will underperform here.
   - If the intent mentions "deep" / "thorough" / "full treatment" / "explore every angle" / "dig in" / "comprehensive": use `deep_explore`.
   - If the intent mentions "score" / "rank" / "prioritize formally": use `quick_seed` (adds scoring to `starter`'s shape).
   - If the intent mentions reframing a prior problem: `reframe_and_regenerate` (only valid if the topic already has a frame — if not, fall back to `starter` and note the reframe in its output).
   - **Default (none of the above matched): `starter`.** Lightweight frame + 20 ideas + a compare report. One checkpoint. Pick this when the intent has no clear signal.

4. Else (the topic has ideas but the intent doesn't match a playbook shape):

   **4a.** If the intent mentions "route" / "iterate" / "keep developing" / "what should I try next" / "plan next moves" AND the topic has ≥5 active ideas: use the `route` playbook. This is the iterative follow-up shape — the router decides what to do with each idea based on current state, rather than applying a single operator to the whole batch.

   **4b.** Otherwise:
   - Emit a custom 3–8 step plan using the operator library as vocabulary.
   - Example: intent "find weak ideas" → `evaluate.score cohort=all_active` + `decide.shortlist cohort=bottom-20%` + `decide.compare`.
   - Example: intent "what ideas haven't been stressed yet" → `decide.compare cohort=<ideas without web_stress_verdict>`.

## Checkpoint insertion

After you draft the plan, insert these checkpoints (unless the user passed --no-checkpoints, unless they are already present, OR unless the user's intent explicitly names a playbook — playbooks carry their own checkpoints):

- After `frame.discover`: `CHECKPOINT: framing`
- After `evaluate.criteria`: `CHECKPOINT: criteria_lock`
- Before any `validate.*` affecting more than 5 ideas: `CHECKPOINT: before_validation`
- Before `decide.converge` or `decide.export`: `CHECKPOINT: before_decide`
- If the plan will generate more than 30 new ideas before any evaluation: `CHECKPOINT: taste` after the generation phase

## Your output

Write the plan so a human can skim it and understand what will happen. Lead each step with a plain-language sentence; put the machine-readable tag in parentheses at the end so the orchestrator can execute it. Keep sentences short and specific.

Output this exact format:

```
## Plan

1. <one-sentence human description> (<operator.name> [key=value ...] [cohort=...])
2. <one-sentence human description> (<operator.name> ...)
3. ⏸ Checkpoint — <what the user will confirm in their own words>
4. <short overview of the fan-out>. In parallel:
   - <natural sub-step description> (<operator.name> ...)
   - <natural sub-step description> (<operator.name> ...)
...

## Rationale

<2-3 sentences: which playbook you chose (or why you emitted a custom plan) and what outcome the user should expect>
```

### Example — the DEFAULT shape (starter playbook)

Most first-time invocations on a fresh topic should produce a short plan like this:

```
## Plan

1. Identify root causes and framing questions (frame.discover)
2. ⏸ Checkpoint — confirm the framing before generating ideas
3. Generate ~20 diverse ideas in parallel:
   - Practical, contradiction-driven ideas — 10 (generate.seed persona=innovator count=10)
   - Wild, random-stimulus ideas — 10 (generate.seed persona=wild_card count=10)
4. Present them side-by-side in a short report (decide.compare cohort=all_active)

## Rationale

Running the `starter` playbook — the default for fresh topics. Light frame, two personas, a compare report. No scoring, no web research. If the output warrants it, follow up with `ideation <slug>: stress-test the top 3` or `ideation <slug>: develop idea N`.
```

Four steps, one checkpoint, ~20 ideas, one report. Keep plans this tight by default.

### Example — opt-in heavy shape (deep_explore)

When the user says "thorough" / "deep" / "full treatment", emit a longer plan:

```
## Plan

1. Scout the web for citable grounding facts about the problem (frame.context_scout)
2. Identify root causes, framing questions, and the core trade-off (frame.discover)
3. ⏸ Checkpoint — confirm the framing before generating ideas
4. Generate raw seed ideas from four personas in parallel:
   - Practical, contradiction-driven ideas — 15 (generate.seed persona=innovator count=15)
   - Reverse-brainstormed ideas — 12 (generate.seed persona=provocateur count=12)
   - Wild, random-stimulus ideas — 15 (generate.seed persona=wild_card count=15)
   - Cross-domain analogies — 12 (generate.seed persona=connector count=12)
5. Push every seed wilder, ground it in a real mechanism, and pressure-test it:
   - Push wilder (transform.john zone=FIRE stance=dreamer_start cohort=all_seeds)
   - Ground with cross-domain mechanism (transform.john zone=PLASMA stance=realist_start cohort=all_seeds)
   - Pressure-test for feasibility (transform.john zone=ICE stance=critic_start cohort=all_seeds)
6. Find tensions between ideas (evaluate.tension cohort=all_active)
7. Synthesize across the hottest tensions, 2 cycles (transform.ratchet zone=FIRE cycles=2 cohort=tension_cluster)
8. ⏸ Checkpoint — taste check
9. Combine a diverse slate of 5 ideas into hybrids (transform.hybridize cohort=diversity-top(5))
10. Derive evaluation criteria (evaluate.criteria)
11. ⏸ Checkpoint — lock the criteria
12. Score every active idea against the criteria (evaluate.score cohort=all_active)
13. ⏸ Checkpoint — confirm before adversarial validation
14. Stress-test the top 8 with web research (validate.web_stress cohort=top-by-composite(8))
15. Surface brilliance signals on the top 5 (evaluate.brilliance cohort=top-by-composite(5))
16. ⏸ Checkpoint — confirm before final decision
17. Converge on 1-3 selected ideas (decide.converge cohort=top-by-composite(3))
18. Export an Idea Menu (quick wins / core bets / moonshots) (decide.export format=menu)

## Rationale

Running the full `deep_explore` playbook because the user asked for a thorough treatment. Expect ~50-80 active ideas at peak, narrowed to 3 selected at the end.
```

## Format rules

- Every step starts with a plain-language sentence the user can read without knowing operator names.
- The parenthesized tag at the end contains the exact operator name plus params and cohort, space-separated. The orchestrator parses this.
- CHECKPOINT lines start with `⏸ Checkpoint — ` followed by a human sentence explaining what the user will confirm.
- PARALLEL blocks lead with a one-line overview of the fan-out, then nest sub-steps with `-` bullets. Each bullet carries its own human description + machine tag.
- cohort can be:
  - literal IDs: `cohort=[17,24]`
  - named query: `cohort=top-by-composite(5)`, `cohort=top-by-metric(metric=taste, n=3)`, `cohort=children_of(17)`, `cohort=tension_cluster`, `cohort=all_seeds`, `cohort=all_active`, `cohort=diversity-top(5)`
  - step reference: `cohort=children_of(step 1)` — orchestrator resolves at execution time
- params use simple `name=value`. No quotes needed for single-word values.
- Keep human descriptions short (one line each). Avoid methodology jargon in the prose — say "push wilder" not "apply Disney dreamer-mode", say "stress-test" not "run adversarial web search". The parenthesized tag has the precision; the prose is for the human reading.

## Things you must NOT do

- Do not invent operator names. Use only what's in the catalog.
- Do not pass abstract cohorts the orchestrator cannot resolve ("the good ones", "the bold ideas") — translate to concrete queries (`top-by-composite(5)`, `cohort=[ideas WHERE tag='BOLD']` is NOT valid; use a named query like `tension_cluster` or a concrete list).
- Do not fabricate criteria or scores. If the plan needs scoring, include `evaluate.criteria` + `evaluate.score` explicitly.
- Do not emit any operator that reads or writes a frame other than via the frame.* operators.
```

After the planner returns, parse the `## Plan` and `## Rationale` sections.

### Step 4 — Approve the plan with the user

The planner emits plans in the human-readable format above. Show the plan + rationale verbatim via `AskUserQuestion`:

```
Plan for "<intent>":

<paste the ## Plan section verbatim — the prose leads, the parenthesized tags stay but read as brief technical anchors>

Rationale: <rationale text>

Options: Accept / Edit (Other) / Cancel
```

On Accept: proceed.
On Edit (any Other response): send the user's edit back to the planner with the original plan as context; it emits a revised plan. Re-present. Repeat until accepted or cancelled.
On Cancel: stop.

### Step 5 — Execute the plan

For each step in order:

#### Step 5A — Checkpoint lines (`⏸ Checkpoint — ...`)

Do NOT spawn a subagent. Identify which built-in checkpoint this is by the human description the planner emitted (e.g. "confirm the framing" → framing). Call `AskUserQuestion` with the matching payload:

- **framing** — show the active frame (root causes, framing questions, and the trade-off if present). Read via `ideation_db.py active-frame <slug>` and render in plain prose, not as JSON. Options: "Looks right, proceed" / "Let me edit (Other)".
- **taste** — delegate to `evaluate.taste_check` as a real operator invocation; the orchestrator replaces this checkpoint line with a regular operator execution over a diverse slate of recent seeds + transforms.
- **criteria_lock** — read the latest `./.ideation/<slug>/criteria-<run_id>.json` file and render the criteria + weights as a plain list. Options: "Accept criteria" / "Adjust (Other)". On Adjust, rewrite the criteria file with user edits before proceeding.
- **before_validation** — show how many ideas are about to be validated + a short sample of their titles. Options: "Proceed" / "Narrow the list (Other)" / "Skip validation".
- **before_decide** — show the current top N ideas (titles + evidence posture). Options: "Proceed to decide" / "Run one more pass (Other)" / "Skip".
- **custom** — the step carries its own `question` and `options` params; present them.

Record the outcome in `operator_runs` — when any operator runs after a checkpoint, pass `--user-approved` (true if the user proceeded; false if they explicitly skipped). If the user bails at a checkpoint, stop the plan cleanly and write a summary of what ran up to that point.

#### Step 5B — Regular operator steps

For each non-checkpoint step:

1. **Resolve the cohort to literal IDs.**
   - Literal IDs → already concrete.
   - Named query → run `ideation_db.py query <slug> <query-name> [--n N] [--metric ...] [--id ...]`.
   - Step reference (e.g., `children_of(step 1)`) → query the logbook based on what the referenced step produced (typically `ideation_db.py children-of <slug> <parent_id>` per parent).

2. **Create the operator_runs row.**

   ```bash
   OP_RUN_ID=$(ideation_db.py op-start <slug> \
     --run-id $RUN_ID \
     --plan-step <N> \
     --operator <fully.qualified.name> \
     [--persona <persona>] \
     --cohort-ids-json '<JSON array>' \
     [--params-json '<JSON object>'])
   ```

3. **Spawn the operator subagent** via the `Agent` tool. Pass it:
   - The operator file content (read `operators/<operator>.md`).
   - The topic slug.
   - The literal cohort_ids.
   - The resolved params.
   - `$RUN_ID`.
   - `$OP_RUN_ID`.
   - Any persona/zone reference files the operator needs (read them and include inline).

   The operator subagent executes its prompt body, runs CLI commands, writes rows tagged with `$OP_RUN_ID`, and returns a 1-3 sentence outcome summary.

4. **Finalize the row.**

   On success:
   ```bash
   ideation_db.py op-finalize <slug> $OP_RUN_ID \
     --status succeeded --outcome-summary "<from subagent>"
   ```

   On failure:
   ```bash
   ideation_db.py op-finalize <slug> $OP_RUN_ID \
     --status failed --error "<failure reason>"
   ```

5. **Retry policy.** If the operator fails, retry once. If it fails again, mark it `failed`, print a warning to the user, and continue to the next step unless the failure cascades (e.g., subsequent steps depended on output from the failed one — in that case, ask the user whether to continue or stop).

#### Step 5C — PARALLEL blocks

PARALLEL blocks are the mechanism for fan-out (multiple `generate.seed` personas, multiple `transform.john` zones, etc.).

Execute by spawning all sub-steps in **one message** using multiple `Agent` tool calls. For each sub-step:
- Create its own `operator_runs` row before spawning (ahead of time, so each subagent knows its `operator_run_id`).
- Spawn all subagents in parallel.
- Collect all their outcome summaries.
- Finalize each `operator_runs` row as the subagents return.

Do not proceed past the PARALLEL block until all its sub-steps have terminated.

#### Step 5D — `decide.route` fragment expansion

When the step you just executed is a `decide.route` call, the normal Step 5B flow changes: **defer the `op-finalize` on the `decide.route` row until after the fragment has been read and validated**, so the outcome summary records both the subagent's decisions and any validation drops in a single finalize.

If `decide.route` itself fails (subagent returns an error, raises an exception, or fails twice under Step 5B's retry policy), do NOT enter this expansion flow — apply Step 5B's normal failure handling and stop. Step 5D only runs on a confirmed successful `decide.route` return.

1. After the `decide.route` subagent returns its outcome summary, do NOT call `op-finalize` yet. Keep the summary in a local variable as `subagent_summary`.
2. Read `./.ideation/<slug>/reports/<RUN_ID>-route.md` — the subagent wrote this during its operator work.
3. Extract the `## Plan fragment` section. Its grammar is narrow:
   - Exactly one `PARALLEL:` header line.
   - Zero or more `- <operator.name> [key=value ...] cohort=[id, id, ...]` bullets.
   - Parse each bullet: operator name, params (space-separated `key=value`), cohort (literal integer IDs).
4. **Validate every recommended operator call** against the operator catalog (reload via `ideation_db.py list-operators --format json` if you don't already have it cached for this session):
   - Operator name exists in the catalog.
   - `cohort size >= applies_to.min_cohort`.
   - If `applies_to.kinds` is non-empty, every idea in the cohort has `kind` ∈ those kinds (read via `ideation_db.py idea <slug> <id>`).
   - If the parent `decide.route` was invoked with `params.cheap=true`, drop any bullet whose operator has `cost.web: true`.
   - For each idea in the bullet's cohort, query `ideation_db.py lineage-ops <slug> <id> --limit <cooldown + 1>` to retrieve the idea's lineage-ops history. If the bullet's operator name appears within the last `repeat_guard.same_lineage_cooldown` entries for ANY cohort idea, drop the bullet. Defense in depth — the subagent should already have respected this, but the orchestrator enforces it definitively.
   - Collect dropped bullets + reasons in a local `drops` list; print a warning per drop.
5. Compute the combined finalize summary:
   - If `drops` is empty: `final_summary = subagent_summary`.
   - Otherwise: `final_summary = subagent_summary + "; dropped during validation: " + "; ".join(drops)`.
6. Call `op-finalize <slug> <decide.route op_run_id> --status succeeded --outcome-summary "<final_summary>"` — this is the first and only finalize of the `decide.route` row.
7. If the validated fragment is empty or every bullet was dropped, proceed to the next plan step. Print "Fragment empty — nothing to expand" to the user.
8. Otherwise, treat the validated bullets as a PARALLEL block and execute them using the normal Step 5C parallel-dispatch. Each bullet gets its own `operator_runs` row:
   - Call `op-start` with `--run-id $RUN_ID` but **omit `--plan-step`** (so `plan_step_index` stores `NULL` — these are fragment-expanded, not in the planner's original plan).
   - Construct a single JSON object containing BOTH the parent-linkage keys AND every `key=value` pair parsed from the bullet. For example, if the bullet was `transform.scamper count=3 cohort=[8]`, the params JSON is `{"parent_operator_run_id": <decide.route op_run_id>, "parent_plan_step_index": <decide.route plan_step>, "count": 3}`. Pass this as `--params-json`.
   - Spawn each subagent per the normal Step 5B procedure.
   - Finalize each row as subagents return.

Fragment expansion shares the outer plan's `RUN_ID` — querying `operator_runs` filtered by `RUN_ID` reconstructs the full session.

### Step 6 — Post-run summary

After the last step, render a human-readable summary. Lead with what changed; keep counts tight; skip internal terminology.

```
Done. Here's what this session produced:

- Generated <X> new ideas (<seeds> raw seeds, <variants> variants, <hybrids> hybrids)
- Recorded <Y> new pieces of evidence from the web
- Made <Z> judgments across <K> different metrics
- <count> ideas shortlisted, <count> selected, <count> rejected
- Reports:
    · ./.ideation/<slug>/reports/<run_id>-<report>.md
    · ...

Try next:
- Develop a specific idea further: `ideation <slug>: develop idea N`
- Combine two ideas: `ideation <slug>: hybridize N and M`
- Stress-test the strongest: `ideation <slug>: stress-test the top 3`
- Just peek at state: `ideation <slug> --show-state`
```

Query the counts via:

```bash
ideation_db.py op-runs <slug> --run-id $RUN_ID
ideation_db.py ideas <slug> --status active
ls ./.ideation/<slug>/reports/
```

Omit zero-count lines. If no ideas were generated (e.g., a decide-only session), say so explicitly — "No new ideas this session; the work was evaluation and decision."

## Operator catalog

Read the files in `operators/` for the full library. Summary:

- `frame.*` — context/problem-space operators (4): `context_scout`, `discover`, `historian`, `reframe`
- `generate.*` — idea producers (2): `seed(persona=...)`, `fresh(hint=...)`
- `transform.*` — idea-to-idea operators (7): `scamper(op=...)`, `invert`, `cross_domain(domain=...)`, `hybridize`, `john(zone=..., stance=...)`, `ratchet(zone=..., cycles=...)`, `refine(hint=...)`
- `evaluate.*` — per-metric judgments (6): `hats`, `tension`, `taste_check`, `criteria`, `score(criteria_path=...)`, `brilliance`
- `validate.*` — web-sourced evidence (2): `web_stress`, `proof_search`
- `decide.*` — report/decision artifacts (4): `shortlist(n=...)`, `compare`, `converge`, `export(format=...)`

## Playbook catalog

See `playbooks/<name>.md` for full shapes. Summary:

- **`starter`** — **default**. Frame + 20 ideas + compare. 1 checkpoint. ~5 min.
- `quick_seed` — `starter` plus criteria + scoring. 2 checkpoints. ~10 min.
- `naming` — specialized for naming (products, features, companies). 70 candidates across 5 naming angles + web validation. ~10 min.
- `deep_explore` — full treatment for fresh problems (four personas, Johns, ratchet, web-stress, brilliance, converge). Opt-in only.
- `followup_develop` — develop specific ideas further
- `hybridize_pair` — combine specific ideas
- `stress_test_shortlist` — validate a shortlist with web evidence
- `reframe_and_regenerate` — mid-session pivot (new frame, regenerate)
- `converge_existing` — no new ideas, just decide on the current pool
- `route` — state-driven follow-up; router subagent decides per-idea operator assignments. Accepts `--loop`, `--cheap`, `--with-criteria`, `--iterations N`.

## Cohort query mapping

The planner emits cohort references; the orchestrator resolves them via the CLI:

| Cohort spec | CLI call |
|---|---|
| `top-by-composite(5)` | `ideation_db.py query <slug> top-by-composite --n 5` |
| `top-by-metric(metric=taste, n=3)` | `ideation_db.py query <slug> top-by-metric --metric taste --n 3` |
| `children_of(17)` | `ideation_db.py query <slug> children-of --id 17` |
| `tension_cluster` | `ideation_db.py query <slug> tension-cluster` |
| `all_seeds` | `ideation_db.py query <slug> all-seeds` |
| `all_active` | `ideation_db.py query <slug> all-active` |
| `all_active_capped(50)` | `ideation_db.py query <slug> all-active-capped --n 50` |
| `diversity-top(5)` | `ideation_db.py query <slug> diversity-top --n 5` |
| literal IDs `[17, 24]` | no CLI call needed; pass through |
| `children_of(step N)` | for each idea produced by step N (from its operator_runs row's subsequent inserts), call `children-of` |

## References

- `ideation.logbook.md` — authoritative schema, identity rules, correction rules, queries, governance
- `references/operations.md` — the creative ops toolkit (SCAMPER, TRIZ, Six Hats, Synectics, Reverse Brainstorming)
- `references/output-rules.md` — mandatory style rules (coffee-talk descriptions, ID discipline, no methodology names in user-facing text)
- `references/personas/<name>.md` — specialist voices loaded by parameterized operators
- `references/zones/<name>.md` — temperature-zone constraints loaded by `transform.john` and `transform.ratchet`

## Tool usage reminders

- Use the `Agent` tool to spawn planner and operator subagents.
- Use `AskUserQuestion` for every checkpoint and for plan approval.
- Spawn PARALLEL sub-steps in a single message (multiple Agent tool calls), not sequentially.
- Never skip `op-start` / `op-finalize` — the `operator_runs` table is the audit log; missing rows break follow-up sessions.
- Operators never call `op-start` or `op-finalize` — that is exclusively the orchestrator's job.
