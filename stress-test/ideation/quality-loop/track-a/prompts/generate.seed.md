---
name: generate.seed
stage: generate
scope: pool
applies_to:
  kinds: []
  min_cohort: 1
use_when:
  - pool is empty or needs a fresh persona injection
  - user asks for a specific persona's take
avoid_when:
  - pool is already saturated with seeds — transform or evaluate instead
produces:
  ideas: true
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 0
followups:
  - evaluate.taste_check
  - decide.compare
---

# Operator: generate.seed

Produce a batch of raw seed ideas, parameterized by a specialist persona voice.

## Inputs

- `cohort_ids`: ignored — seeding takes no parent ideas (empty `[]`).
- `params`:
  - `persona` (string, required) — one of `innovator`, `provocateur`, `connector`, `wild_card`. Determines which persona file is loaded from `references/personas/<persona>.md`.
  - `count` (int, default `12`) — target seed count. Persona-typical ranges: innovator 12–18, provocateur 10–15, connector 10–15, wild_card 12–18.
  - `emphasis` (string, optional) — free-text hint to bias the persona (e.g. "focus on pricing mechanisms", "lean into regulatory angles").

## Outputs

Writes to:
- `ideas` rows: `count` new rows, `kind=seed`. Each tagged `SAFE`/`BOLD`/`WILD` per persona defaults. No lineage (seeds have no parents in this operator).

## Reads

- Active frame (via `active-frame`) — problem statement, root causes, HMW questions, TRIZ trade-off, IFR.
- `facts` — citable context for grounding. If any exist, at least one seed in the batch must embed a cited fact.
- Persona file — loaded from `references/personas/<persona>.md` and followed literally.

## Prompt body

You are a seed factory operating under the voice defined in `references/personas/<persona>.md`. Load that file first; it tells you how to think, which moves to favor, and what to watch out for. Honor it — do not mix personas or drift into a generalist voice.

### Step 1 — Read the frame and the persona

Read the active frame. Note:
- The problem statement (one sentence)
- The full list of root causes
- All HMW questions (each points in a different direction; let the persona pick which ones to lean on)
- The TRIZ trade-off if present (especially important for the Innovator persona)
- The IFR (especially relevant for the Connector persona's Fantasy analogy and the Wild Card's stimulus hunts)

Then load and re-read the persona file. Internalize the voice before writing seeds.

### Step 2 — Read grounding facts

Query facts. If any exist, you **must** cite at least one in a seed's description. Prefer strong-confidence facts; adversarial facts are welcome input — especially for Provocateur-style inversions — but don't privilege them over confirming ones. If there are no facts, the grounding requirement is waived.

### Step 3 — Generate seeds

Follow the persona's signature moves and output rules. Target `count` seeds. Speed over polish — one mechanism and one concrete example per seed.

Each seed must advance the frame's **stated goal**, not an adjacent proxy — solving a near-neighbour problem (e.g. recovering a loss rather than creating new value) is a relevance miss. And if the frame names an explicit constraint ("do X *without* Y"), a seed that risks violating Y is off-frame however clever. If a root cause is time-bound (a window, deadline, or moment), a seed whose payoff lands or *accrues* after that window misses the cause even if it helps later — starting inside the window is not paying off inside it. Check the lever bites *inside* the named window.

- Spread tags: a healthy batch mixes `SAFE`, `BOLD`, and `WILD` unless the persona has a hard tag bias (Wild Card: ≥50% WILD; Provocateur: full spread).
- Distinct mechanisms: name each seed's core lever as a five-word who-does-what action before committing; if two names match, it's one lever. Seeds collapse when they differ only in *what they surface, count, or measure* (a tally is a tally), in louder or polished wording, or — the costume trap — wear a different surface or target yet pull the same lever. When seeds collapse, keep the strongest and rebuild the rest on a structurally different lever aimed at the same root cause.
- Beat the obvious default: strip your method and ask if a domain generalist would name the same move unprompted. If so — or if it's the move *any* persona lands on regardless of method — it's a warmup, not a find. Replace it.
- Honor the persona's "watch out for" warnings — they kill seed batches.

### Step 4 — Apply the emphasis hint

If `params.emphasis` is set, use it to pick which HMW questions to lean on or which domains to sweep — but don't let it collapse the batch to one mechanism. It's a direction, not a constraint.

## Output discipline

- Follow `references/output-rules.md`, including the **Description Writing Protocol** — draft the mechanism internally, then rewrite as coffee-talk (2–3 sentences, concrete example mandatory). No jargon or methodology names in `description`. Titles name who-does-what, not a positioning slogan.
- Seeds are independent atoms; no inline lineage here.
- One persona per batch. For multiple voices, the orchestrator reruns `generate.seed` with different `persona` params.

## Commands

Read active frame + facts:
```bash
python scripts/ideation_db.py active-frame $SLUG
sqlite3 ./.logbooks/ideation/$SLUG/logbook.sqlite \
  "SELECT fact_id, claim, confidence, stance FROM facts ORDER BY confidence DESC;"
```

Load persona:
```bash
cat plugins/ideation/skills/ideation/references/personas/$PERSONA.md
```

Write seeds in bulk (more efficient than one-at-a-time):
```bash
python scripts/ideation_db.py add-ideas-batch $SLUG ideas.json \
  --origin-operator-run-id $OPERATOR_RUN_ID
```

Where `ideas.json` is a JSON array:
```json
[
  {"title": "...", "description": "...", "kind": "seed", "tag": "BOLD"},
  {"title": "...", "description": "...", "kind": "seed", "tag": "WILD"}
]
```

## Return

Report: persona used; number of seeds written; tag distribution (SAFE/BOLD/WILD counts); whether the grounding requirement was met (which fact_id cited, if any); any seed ideas that were drafted but dropped because they collapsed to the same mechanism.
