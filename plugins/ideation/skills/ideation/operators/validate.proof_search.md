# Operator: validate.proof_search

Narrow, targeted web-search validation of a specific claim embedded in an idea's description — not a full adversarial sweep. Use after `evaluate.score` or `evaluate.brilliance` when the user wants a lighter check on one or two candidates before promoting.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to run proof searches on. Typically 1-3 — this is a focused operator, not a batch one.
- `params`:
  - `claim` (string, required) — the specific factual claim to verify. Example: `"Competitors in this category charge €40-80"` or `"Regulators classify this as a medical device"`. The operator runs 2-4 web searches around this one claim.
  - `max_queries` (int, default 4) — hard cap on `WebSearch` / `WebFetch` calls per idea.

## Outputs

- `facts` rows: one per citable claim found (supporting OR adversarial). Every fact carries `source_url` or `source_label`.
- `assessments` rows:
  - `metric=proof_verdict` — `value` one of `supported|refuted|inconclusive`. `rationale` summarizes what the search turned up in one sentence. `evidence_fact_ids` lists backing fact IDs.
- `ideas` mutable-field patches: `evidence_state` patched per the rule below, but only when the verdict is decisive.

## Reads

- Active frame via `active-frame` (root causes).
- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID`.
- Existing facts via `ideation_db.py facts $SLUG` — do not duplicate claims already captured.

## Prompt body

This is the lighter sibling of `validate.web_stress`. You are NOT running attack rounds. You are checking one specific claim the idea relies on.

**Process per idea:**

1. **Frame the claim as a search target.** Translate `params.claim` into 2-4 specific queries. Examples:
   - For pricing claim: `"[product category] pricing 2025 Europe"`, `"[competitor name] review site"`.
   - For regulatory claim: `"[jurisdiction] [product category] regulation 2024"`, `"FDA / CE classification [feature]"`.
   - For market-size claim: `"[market] size growth 2025 report"`, `"[target audience] number of users 2024"`.

2. **Run `max_queries` or fewer searches.** Stop early when the claim is clearly supported or clearly refuted.

3. **Write citable facts.** Every claim you surface becomes a `facts` row with `source_url` + `source_label` and a stance relative to the claim (not relative to the idea — a supporting fact for the claim may be adversarial for the idea, depending on context).

4. **Verdict:**
   - `supported` — ≥1 strong OR ≥2 medium-confidence supporting facts found; no contradicting strong facts.
   - `refuted` — ≥1 strong contradicting fact OR ≥2 medium-confidence contradicting facts.
   - `inconclusive` — no citable evidence either way within `max_queries`. Record this honestly; inconclusive is a valid verdict.

5. **Evidence-state patch (only when decisive):**
   - `supported` → patch `ideas.evidence_state = 'supported'` ONLY if there's no prior stronger `disputed` verdict from `validate.web_stress`.
   - `refuted` → patch `ideas.evidence_state = 'disputed'` unless a prior `supported` verdict from `validate.web_stress` is already in place (in which case leave it; the richer sweep wins).
   - `inconclusive` → leave `evidence_state` untouched.

## Output discipline

- Follow `references/output-rules.md`. Facts are 1-2 sentences; `claim` ≤ 300 characters.
- `rationale` names the specific claim checked, the result, and the strongest piece of evidence. No methodology names.
- This operator does NOT write `brilliance.*` or scoring assessments. Only facts and a single `proof_verdict` per idea.
- If a fact came from a page the operator fetched but couldn't verify source freshness, set `confidence='weak'`.

## Commands

**Batch every write.** This operator is light (1-3 ideas) but still batches: one `add-facts-batch` for every new fact, one `add-assessments-batch` for every `proof_verdict` row, and — only when verdicts are decisive — one `patch-ideas-batch` for `evidence_state`. Maximum 3 write subprocess calls total regardless of cohort size. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read context (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py idea $SLUG $IDEA_ID
python scripts/ideation_db.py facts $SLUG

# STEP 1: Write ALL new facts in one batch. Do this first so you know the fact_ids
# to cite in each verdict's evidence_fact_ids.
cat > /tmp/proof-facts-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"claim": "G2 lists 4 competitors in the €40-€80 price band with 100+ reviews each as of 2025-Q3.",
   "confidence": "strong", "stance": "supports",
   "source_url": "https://g2.com/...",
   "source_label": "G2 category page, 2025-Q3"}
]
JSON

python scripts/ideation_db.py add-facts-batch $SLUG /tmp/proof-facts-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/proof-facts-$OPERATOR_RUN_ID.json

# STEP 2: Write ALL proof_verdict assessments in one batch (one per cohort idea).
cat > /tmp/proof-verdicts-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 47, "metric": "proof_verdict", "value": "supported",
   "rationale": "Checked the pricing-band claim: 4 competitors listed in that exact range, each with significant review volume.",
   "evidence_fact_ids": [22]}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/proof-verdicts-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/proof-verdicts-$OPERATOR_RUN_ID.json

# STEP 3 (only when any verdict is decisive): patch evidence_state for those ideas.
cat > /tmp/proof-patch-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 47, "column": "evidence_state", "value": "supported"}
]
JSON

python scripts/ideation_db.py patch-ideas-batch $SLUG /tmp/proof-patch-$OPERATOR_RUN_ID.json

rm -f /tmp/proof-patch-$OPERATOR_RUN_ID.json
```

**Do not** call `add-fact`, `add-assessment`, or `patch-idea` per row. The batch form is strictly faster and preserves transactional atomicity.

## Return

A 1-3 sentence outcome summary: claim checked, verdict per idea, number of facts written (split by stance), and any `evidence_state` patches applied. Explicitly note `inconclusive` verdicts — they tell the orchestrator whether to schedule a heavier `validate.web_stress` pass.
