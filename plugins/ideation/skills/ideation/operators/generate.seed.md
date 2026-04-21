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

Query facts. If any exist, you **must** cite at least one in a seed's description (e.g., "Building on Nielsen's 2024 finding that 68% of freelancers switched platforms in the last year…"). Prefer strong-confidence facts; adversarial facts are welcome input — especially for Provocateur-style inversions — but don't privilege them over confirming ones. If there are no facts, the grounding requirement is waived.

### Step 3 — Generate seeds

Follow the persona's signature moves and output rules. Target `count` seeds. Speed over polish — one mechanism per seed, one concrete example per description, no timelines or step lists inside the description.

- Spread tags: a healthy batch mixes `SAFE`, `BOLD`, and `WILD` unless the persona has a hard tag bias (Wild Card: ≥50% WILD; Provocateur: full spread).
- Distinct mechanisms: if every seed boils down to the same move (e.g., "make it modular"), rotate your stimulus sources.
- Honor the persona's "watch out for" warnings — they are the failure modes that kill seed batches.

### Step 4 — Apply the emphasis hint

If `params.emphasis` is set, use it as a filter on which HMW questions to lean on or which domains to sweep — but do not let it collapse the batch to one mechanism. The emphasis is a direction, not a constraint.

## Output discipline

- Follow `references/output-rules.md`.
- Coffee-talk descriptions: 2–3 sentences, concrete example mandatory. No jargon, no methodology names in the `description` field (readers never see "SCAMPER" or "TRIZ").
- Titles are 3–80 chars, no numbering, no prefixes like "Idea #1:".
- Seeds are independent atoms; no inline lineage for this operator.
- One persona per batch. If the orchestrator wants multiple voices, it runs `generate.seed` multiple times with different `persona` params.

## Commands

Read active frame + facts:
```bash
python scripts/ideation_db.py active-frame $SLUG
sqlite3 ./.ideation/$SLUG/logbook.sqlite \
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
