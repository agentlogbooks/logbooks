# Operator: evaluate.brilliance

Qualitative judgment pass on the top-scored cohort. Writes a brilliance scorecard and, where warranted, patches `evidence_state` to reflect that an idea has structural weight beyond its composite score.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s — typically the top 8-12 by `score_summary`, plus any ideas flagged by `decide.shortlist`.
- `params`:
  - `max_brilliant` (int, default 3) — hard cap on ideas rated BRILLIANT. Zero is a valid output.
  - `patch_evidence_state` (bool, default true) — when true, an idea with BRILLIANT + a strong web-stress verdict is patched to `evidence_state='supported'`; a BRILLIANT with a refuted web-stress verdict is patched to `stressed`.

## Outputs

- `assessments` rows per evaluated idea, all with `metric=brilliance.<dimension>`:
  - `brilliance.one_insight` — `yes|no`; `rationale` states the single insight in one sentence (or explains the failure).
  - `brilliance.hindsight` — `yes|no`
  - `brilliance.compounding` — `yes|no`
  - `brilliance.parsimony` — `yes|no` (solves 2+ problems with 1 mechanism)
  - `brilliance.resolves_tension` — `yes|no` (resolves a tension surfaced by `evaluate.tension`)
  - `brilliance.both_sides_accept` — `yes|no`
  - `brilliance.load_bearing` — `yes|no` (what breaks if you remove this idea?)
  - `brilliance.tier` — `brilliant|notable|—`; `value_numeric` = count of yes answers (0-7); `rationale` = one-sentence pitch for brilliant ideas.
- `ideas` patches (optional): `evidence_state` set to `supported` or `stressed` per the rule in `params.patch_evidence_state`.

## Reads

- Active frame via `active-frame` (root causes — ideas that hit the root cause directly score higher on tension and load-bearing).
- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID`.
- Prior assessments for the cohort: `ideation_db.py latest-assessment` per key metric; also prior `tension.*` rows (for the resolves_tension question) and `web_stress_verdict` / `proof_verdict` (for the evidence_state patch).

## Prompt body

You are NOT re-scoring on criteria — that's done. You are looking for structural elegance, surprise, and inevitability. The ideas that make people say "why didn't we think of this before?"

**The 7 brilliance questions.** For each cohort idea, answer all seven with `yes` or `no`:

1. Can you state the ONE insight that makes this work in a single crisp sentence? (Paragraph needed → no.)
2. Would an expert say "obvious in hindsight"? (Expert says "we already do this" → no.)
3. Does this get MORE valuable over time? (Only works in current conditions → no.)
4. Does it solve 2+ problems with one mechanism? (Solves exactly one → no.)
5. Does it resolve a tension this session surfaced? (Ignores the core contradiction → no.)
6. Would both sides of a disagreement accept this? (Only one side wins → no.)
7. What breaks if you remove this idea from the set? (Nothing → no.)

**Tiers:**
- 5-7 `yes` → BRILLIANT. Cap at `max_brilliant` per run; if more candidates qualify, pick the ones with the sharpest one-insight sentences.
- 4 `yes` → NOTABLE.
- < 4 `yes` → neither. Write the 7 question rows anyway with `brilliance.tier` value `—`.

**The pitch.** For every BRILLIANT idea, write ONE sentence that captures the structural insight — not the mechanism, not the description. The sentence answers "Why does this idea HAVE to exist? What structural reality makes it inevitable?" This goes in the `rationale` field of the `brilliance.tier` row.

**Evidence state patch (when `patch_evidence_state=true`):** after writing all brilliance rows for an idea:
- If `brilliance.tier` is `brilliant` AND a `web_stress_verdict` = `survives_scrutiny` (or `proof_verdict` = `supported`) exists → patch `ideas.evidence_state = 'supported'`.
- If `brilliance.tier` is `brilliant` AND a `web_stress_verdict` = `refuted` exists → patch `ideas.evidence_state = 'stressed'`.
- Otherwise, leave `evidence_state` untouched.

**Zero BRILLIANT ideas is a valid output.** If the session produced solid practical ideas but nothing structurally surprising, record that. Do not inflate.

## Output discipline

- Follow `references/output-rules.md`. The pitch sentence is the structural insight, not the mechanism. "Build a dashboard that shows conflicts" is a mechanism; "The AI can hold 500 applications in memory at once — no human team can — so cross-cutting collision detection becomes possible for the first time" is the insight.
- No scores or multipliers in user-visible output. The `brilliance.tier` value is an enum label, never a number in prose.
- Do NOT mutate `score_summary`. Scoring belongs to `evaluate.score`.

## Commands

**Batch every write.** For a cohort of N, this operator should produce exactly 1–2 write subprocess calls total (one `add-assessments-batch` for the 8×N brilliance rows, plus at most one `patch-ideas-batch` if any `evidence_state` patches are warranted), no matter how many ideas you evaluate. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read context (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py idea $SLUG $IDEA_ID
python scripts/ideation_db.py latest-assessment $SLUG --idea-id 12 --metric web_stress_verdict

# Build ALL 8×N brilliance assessments (7 questions + tier row per idea) into one tempfile.
cat > /tmp/brilliance-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "brilliance.one_insight", "value": "yes",
   "rationale": "A queue that rewrites itself based on who's waiting means you never have to choose speed vs. fairness."},
  {"idea_id": 12, "metric": "brilliance.hindsight", "value": "yes",
   "rationale": "Every ops lead will say 'of course — we've been doing the dumb version all along.'"},
  {"idea_id": 12, "metric": "brilliance.compounding", "value": "yes",
   "rationale": "Value grows as the queue's history lengthens; more signal, better rewrites."},
  {"idea_id": 12, "metric": "brilliance.parsimony", "value": "yes",
   "rationale": "One mechanism solves both SLA breaches and escalation fatigue."},
  {"idea_id": 12, "metric": "brilliance.resolves_tension", "value": "yes",
   "rationale": "Resolves the speed-vs-fairness tension surfaced in tension.scale_vs_intimacy."},
  {"idea_id": 12, "metric": "brilliance.both_sides_accept", "value": "yes",
   "rationale": "The fairness camp and the speed camp both get what they want."},
  {"idea_id": 12, "metric": "brilliance.load_bearing", "value": "yes",
   "rationale": "Remove it and the shortlist loses its only idea that collapses the trade-off."},
  {"idea_id": 12, "metric": "brilliance.tier", "value": "brilliant", "value_numeric": 7,
   "rationale": "One mechanism — self-rewriting queue — collapses the fairness/speed trade-off the whole market works around."},
  {"idea_id": 34, "metric": "brilliance.one_insight", "value": "no",
   "rationale": "Needs a paragraph to explain; no single sentence captures it."},
  {"idea_id": 34, "metric": "brilliance.tier", "value": "—", "value_numeric": 2,
   "rationale": "Solid but not structurally surprising."}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/brilliance-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/brilliance-$OPERATOR_RUN_ID.json

# Patch evidence_state for any BRILLIANT ideas where the patch rule applies — ONE call.
cat > /tmp/brilliance-patch-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "column": "evidence_state", "value": "supported"}
]
JSON

python scripts/ideation_db.py patch-ideas-batch $SLUG /tmp/brilliance-patch-$OPERATOR_RUN_ID.json

rm -f /tmp/brilliance-patch-$OPERATOR_RUN_ID.json
```

**Do not** call `add-assessment` seven times per idea in a loop. The batch form is strictly faster and preserves transactional atomicity.

## Return

A 1-3 sentence outcome summary: count of BRILLIANT / NOTABLE / neither, any pitch sentences worth highlighting to the orchestrator, and any `evidence_state` patches written.
