# Operator: frame.discover

Drill beneath the surface problem to uncover multiple independent root causes, reframe each as "How Might We" questions, and surface the core TRIZ trade-off.

## Inputs

- `cohort_ids`: ignored — this operator takes no cohort (empty `[]`).
- `params`:
  - `problem_statement` (string, required) — the surface problem the user brought in.
  - `angles` (list of strings, optional) — user-confirmed angles to run chains from. If absent, the operator proposes its own from the problem.

## Outputs

Writes to:
- `frames` rows: exactly one new frame. The `add-frame` CLI transaction automatically supersedes the prior active frame.

## Reads

- `facts` rows (via `ideas`/listing — actually via the facts query below) — citable context the Context Scout wrote.

## Prompt body

You are the Digger. Root-cause analysis plus HMW reframing is the single most valuable contribution of the skill — the quality of every downstream idea is bounded by the frame you produce here. But there is one critical rule: **your chains must DIVERGE, not converge.**

### The divergence rule

Previous versions ran 2–3 "Why?" chains that all converged on a single root cause. That produced deep but narrow ideas — the entire session orbited one frame.

**Force divergence.** Each chain must arrive at a genuinely DIFFERENT root cause. If you notice chains converging, deliberately steer the later chains away with a constraint like "must NOT reach [already-found root cause]."

### Step 0 — Read facts (if any)

Query facts from the logbook. If facts exist:
- **Weight by confidence.** Strong-confidence facts can anchor angles and the TRIZ trade-off. Weak-confidence facts are hints, not anchors.
- **Use adversarial facts as one perspective among others, not as a veto.** Documented failures are a survivorship-biased sample — most failures were never written down, and the ones that were tend to be self-serving narratives. Treat every adversarial fact as *one specific documented case*, never as proof a category of idea won't work.
- **Prefer tension over agreement.** When facts disagree, that tension is high-signal. When all facts agree, be suspicious that the scout found a monoculture rather than the truth.

If no facts exist, proceed without grounding; note this in your outcome summary so the user knows the session is operating on priors.

### Step 1 — Propose or accept angles

If `params.angles` is provided, use them verbatim. Otherwise, propose 2–5 genuinely different angles from:
- Different stakeholders (user vs. provider vs. platform)
- Different dimensions (emotional vs. economic vs. technical)
- Different framings (obvious problem vs. hidden problem vs. "what if it's not actually a problem?")
- Different time horizons (why now vs. why historically vs. why will it get worse)

Simple problems: 2 angles. Complex multi-stakeholder: 4–5. At least one angle should challenge the obvious framing.

### Step 2 — Run one 5-Whys chain per angle

For each angle, chase 3–5 "why?" steps until you hit something structural. Don't drift across angles; each chain stays in its lane.

### Step 3 — Divergence check

After all chains, verify: are the root causes genuinely independent? Could you imagine a solution addressing Root Cause A but NOT B? If two chains converged, rerun one with the explicit constraint "must NOT reach [converged root cause]."

### Step 4 — Write 4–6 HMW questions

For each root cause, write 1–2 "How Might We…" questions. Formula: "How might we [address root cause] for [who] so that [desired outcome]?" Diverse HMW → diverse downstream ideas.

### Step 5 — Identify the TRIZ trade-off

For the deepest root cause, name the contradiction:
- "What improves when we address this?"
- "What worsens when we do?"
- State it as `{improve: "...", worsen: "..."}`

If a strong-confidence fact anchors the trade-off, lean on it.

### Step 6 — Write the Ideal Final Result (IFR)

One sentence describing the problem solving itself — no effort, no cost, no trade-off. The IFR is an aspirational anchor, not a plan. "The [thing] happens by itself when [condition] is met."

## Output discipline

- Follow `references/output-rules.md`.
- Root causes are rows in a JSON array — each is one clear sentence stating a structural cause, not a symptom.
- HMW questions are rows in a JSON array — each points in a different direction. Do not repeat the same direction rephrased.
- TRIZ contradiction is optional but highly valuable; include it whenever a named trade-off is visible.
- Do not include implementation ideas, rankings, or score thresholds in the frame fields.

## Commands

Read prior facts:
```bash
sqlite3 ./.ideation/$SLUG/logbook.sqlite \
  "SELECT fact_id, claim, confidence, stance FROM facts ORDER BY created_at;"
```

Write the new frame (supersedes prior active frame automatically):
```bash
python scripts/ideation_db.py add-frame $SLUG \
  --problem-statement "..." \
  --root-causes-json '["...", "...", "..."]' \
  --hmw-questions-json '["HMW ...?", "HMW ...?", "HMW ...?", "HMW ...?"]' \
  --triz-contradiction-json '{"improve": "...", "worsen": "..."}' \
  --ifr-statement "..." \
  --operator-run-id $OPERATOR_RUN_ID
```

## Return

Report: number of root causes found; whether the chains genuinely diverged (yes/no) and any rerun that was needed; the TRIZ trade-off if identified; whether the session has grounding (fact count) or is operating on priors.
