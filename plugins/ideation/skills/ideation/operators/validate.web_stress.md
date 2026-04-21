# Operator: validate.web_stress

Adversarial validation via web research. For each cohort idea, search for supporting AND refuting real-world evidence, write new `facts` rows for what you find, and record a per-idea `web_stress_verdict`. This operator is the primary source of adversarial facts in the logbook.

## Inputs

- `cohort_ids`: JSON array of integer `idea_id`s to validate. Typically the top 3-8 by `score_summary` (so the web-research cost is spent on ideas worth the check).
- `params`:
  - `rounds_per_idea` (int, default 2) — number of adversarial attack rounds per idea. `3` for a deeper pass.
  - `require_adversarial_fact` (bool, default true) — if true, every idea must produce at least one `stance='adversarial'` fact, even if weak; refusing to find one is not permitted.

## Outputs

- `facts` rows: one per citable claim found. Each has `stance` (`supports|adversarial|neutral`), `confidence` (`strong|medium|weak`), `source_url`, `source_label`. Adversarial facts are the primary value — a supporting fact without an adversarial counterpart is half a job.
- `assessments` rows:
  - `metric=web_stress_verdict` — `value` one of `survives_scrutiny|weakened|refuted`. `value_numeric` optional (1.0 / 0.5 / 0.0). `rationale` summarizes the strongest surviving objection. `evidence_fact_ids` lists the `fact_id`s that back the verdict.
  - `metric=web_stress_attacks` — `value` is a short list of attack types run (e.g. `"market_size; incumbent_response"`). One row per idea.
- `ideas` mutable-field patches: `evidence_state` set to one of:
  - `supported` — if `web_stress_verdict` = `survives_scrutiny` and no strong adversarial fact.
  - `stressed` — if `weakened`: a real objection exists but the idea is not dead.
  - `disputed` — if `refuted`: strong adversarial evidence.
  - Untouched otherwise.

## Reads

- Active frame via `active-frame` (root causes + TRIZ contradiction — tells you which angles to attack).
- Each cohort idea via `ideation_db.py idea $SLUG $IDEA_ID` (title + description are your search anchors).
- Existing facts via `ideation_db.py facts $SLUG` — avoid re-fetching claims already in the logbook.

## Prompt body

You are a red team of one. Your job is to find fatal flaws BEFORE the user commits. Be adversarial by design — a comfortable stress test is useless.

**Do NOT attack feasibility** — scoring already covered that. Attack assumptions and market fit: hidden dependencies, market size, competitive dynamics, regulatory exposure, timing, and structural contradictions the session didn't surface.

**Attack types (pick the most dangerous applicable per round):**

| Attack | The move |
|---|---|
| Market Size | "The addressable market is actually X, which is too small to build a business on." |
| Already Exists | "This already exists as Y. The idea is a re-discovery, not an invention." |
| Hidden Assumption | "This only works if [assumption], which is likely false because…" |
| Dependency Won't Hold | "This depends on [thing] controlled by [someone else / changing / gone]." |
| Timing | "The window is closed / closing / not yet open because…" |
| Too Expensive | "The cost structure doesn't work because…" |
| Regulatory | "Compliance / legal / liability exposure kills adoption." |
| Incumbent Response | "If this works, [big player] copies it in 90 days; the moat doesn't hold." |
| Wrong User | "The people who need this aren't the people who'd pay." |
| Distribution | "There's no credible path to the first 100 users." |

**Process per idea:**

1. **Search for supporting evidence** (WebSearch): 2-3 queries on `"[idea keyword] [market] pricing reviews"`, `"[problem] [audience] forum/reddit"`, competitor listings. For each citable claim found, write a `facts` row with `stance='supports'` and the appropriate confidence.

2. **Search for adversarial evidence** (WebSearch): 2-3 queries on `"[idea keyword] failed shutdown postmortem"`, regulatory hits, incumbent coverage. Write `stance='adversarial'` facts. If `require_adversarial_fact=true`, do not skip this.

3. **Run `rounds_per_idea` attack rounds.** Each round picks one attack type and articulates the strongest version — no strawmen. Per round:
   - Did the idea survive cleanly? → the idea has a genuine response backed by supporting facts.
   - Survived with modification? → note the modification in rationale.
   - Fatal wound? → adversarial fact is strong; survivable → `refuted`.
   - Couldn't land a good objection? → more robust than expected.

4. **Verdict:**
   - `survives_scrutiny` — all rounds survived cleanly, supporting facts strong, adversarial facts weak at most.
   - `weakened` — at least one round required modification OR at least one medium-confidence adversarial fact exists.
   - `refuted` — at least one fatal wound backed by a strong adversarial fact.

5. **Write the verdict** and patch `evidence_state`. Populate `evidence_fact_ids` with the specific `fact_id`s that back the verdict (both supporting and adversarial).

**Interpret evidence honestly:**
- Competitors with many reviews → market validated. Compete on differentiation.
- Competitors with no reviews → market exists but product-market fit unproven.
- No competitors → either blue ocean (rare) or no demand (common). Search demand signals explicitly.
- Failure postmortems exist → read them. Why others failed is your most valuable data.
- Adversarial facts are specific documented cases — they are NOT proof that a category of idea won't work. Most failures aren't documented (survivorship bias). Note this in `rationale` when citing adversarial evidence.

## Output discipline

- Follow `references/output-rules.md`. Facts are 1-2 sentences each; `claim` must be ≤ 300 characters.
- Every fact has a `source_url` OR a `source_label`. No facts written from memory.
- No strawman attacks — if you can't articulate WHY an attack lands with a citable claim, it's not a real objection.
- Do NOT overwrite existing `score_summary` or `brilliance.*` rows. You only write facts, verdict assessments, and the `evidence_state` patch.

## Commands

**Batch every write.** For a cohort of N, this operator should produce exactly 3 write subprocess calls total — one `add-facts-batch` (all new evidence), one `add-assessments-batch` (all `web_stress_verdict` + `web_stress_attacks` rows), and one `patch-ideas-batch` (all `evidence_state` patches) — no matter how many ideas or facts. See `references/output-rules.md` → "Batch writes — mandatory for any high-volume operator" for why.

```bash
# Read context (per-row reads are fine)
python scripts/ideation_db.py active-frame $SLUG
python scripts/ideation_db.py ideas $SLUG --status active
python scripts/ideation_db.py idea $SLUG $IDEA_ID   # repeat per idea only when you need full detail
python scripts/ideation_db.py facts $SLUG

# STEP 1: Write ALL new facts in one batch. Do this FIRST so you know the fact_ids
# to cite in each verdict's evidence_fact_ids. (add-facts-batch returns the inserted IDs
# in order — keep a local map from "claim short-hand" to returned fact_id.)
cat > /tmp/webstress-facts-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"claim": "Three competitors in the EU charge €40-80 for the same feature; review counts 200+ each.",
   "confidence": "strong", "stance": "supports",
   "source_url": "https://example.com/competitor-review",
   "source_label": "TechCrunch roundup, 2025-11"},
  {"claim": "2023 postmortem: similar product shut down within 18 months citing distribution as the fatal issue.",
   "confidence": "medium", "stance": "adversarial",
   "source_url": "https://example.com/postmortem",
   "source_label": "Founder blog, 2023-06"}
]
JSON

python scripts/ideation_db.py add-facts-batch $SLUG /tmp/webstress-facts-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/webstress-facts-$OPERATOR_RUN_ID.json

# STEP 2: Write ALL verdict + attack assessments in one batch (2 rows per idea).
cat > /tmp/webstress-verdicts-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "metric": "web_stress_verdict", "value": "weakened", "value_numeric": 0.5,
   "rationale": "Market exists and is paying, but distribution is the repeated failure mode — the strongest surviving objection.",
   "evidence_fact_ids": [7, 14]},
  {"idea_id": 12, "metric": "web_stress_attacks", "value": "market_size; distribution"},
  {"idea_id": 34, "metric": "web_stress_verdict", "value": "survives_scrutiny", "value_numeric": 1.0,
   "rationale": "All three attack rounds landed without a strong adversarial fact; supporting evidence solid.",
   "evidence_fact_ids": [9]},
  {"idea_id": 34, "metric": "web_stress_attacks", "value": "hidden_assumption; incumbent_response; regulatory"}
]
JSON

python scripts/ideation_db.py add-assessments-batch $SLUG /tmp/webstress-verdicts-$OPERATOR_RUN_ID.json \
  --operator-run-id $OPERATOR_RUN_ID

rm -f /tmp/webstress-verdicts-$OPERATOR_RUN_ID.json

# STEP 3: Patch evidence_state for every idea whose verdict warrants a change — ONE call.
cat > /tmp/webstress-patch-$OPERATOR_RUN_ID.json <<'JSON'
[
  {"idea_id": 12, "column": "evidence_state", "value": "stressed"},
  {"idea_id": 34, "column": "evidence_state", "value": "supported"}
]
JSON

python scripts/ideation_db.py patch-ideas-batch $SLUG /tmp/webstress-patch-$OPERATOR_RUN_ID.json

rm -f /tmp/webstress-patch-$OPERATOR_RUN_ID.json
```

**Do not** call `add-fact`, `add-assessment`, or `patch-idea` per row. The batch form is strictly faster and preserves transactional atomicity.

## Return

A 1-3 sentence outcome summary: count of ideas validated, facts written (split by stance), verdict distribution (survives / weakened / refuted), and any `evidence_state` patches applied.
