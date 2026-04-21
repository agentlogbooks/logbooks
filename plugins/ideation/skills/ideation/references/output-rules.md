# Mandatory Output Rules

These rules apply to every operator subagent — framing, generation, transformation, evaluation, validation, and decision.

## Idea Description Rules

Every idea description — in seeds, variants, hybrids, and refinements alike — must be written like explaining to a colleague over coffee.

- 2-3 sentences max
- First sentence: what is it? (the mechanism, with a concrete example)
- Second sentence: why does it matter? (the impact)
- NO jargon, NO internal terminology, NO references to how the idea was generated
- Self-contained: a reader with zero context should understand it

**Example is mandatory.** "The mechanism" alone is a slogan. The concrete example (who does what, with what, and what happens) is what makes it explainable.

**BAD — procedural, timeline-heavy:**
"Week 1: Run TAM/CAC/churn research on 5 niches. Week 2: Deploy parallel gates on top 2-3. Conviction Score = (Research × 0.4) + (Gate Signals × 0.6). Pick niche > 70%."

**BAD — abstract jargon:**
"AI composition transparency mechanism addressing trust erosion root cause via disclosure tier framework with dynamic fee incentivization."

**GOOD — coffee-talk pitch with concrete example:**
"You stress-test candidate niches before writing a line of code — run €50 ads to 'freelance data analysis for SaaS startups' vs 'freelance data analysis for e-commerce' and pick whichever converts 3x better in a week. You only commit when you're 70% sure, not just hopeful."

If you feel the urge to write "Week 1 / Week 2", a formula, or a step list in the `description` field — stop. Strip it out. Operation lineage lives in the `lineage` table (parent→child edges), not inside prose descriptions.

## Description Writing Protocol

Every operator that writes `ideas` rows (generators and transforms) follows this procedure when drafting each description. It exists because the subagent reasoning about an idea has to write that idea's description, and the reasoning context is jargon-rich. Without an explicit translation step, the vocabulary bleeds through.

### Draft (internal; never committed)

Write one or two sentences describing what the idea is and how it works, using whatever vocabulary comes naturally. Reuse terms from the frame, the facts, the parent ideas, the hint. Name the parts.

This draft is for your own reasoning. It does not enter the `description` field.

### Rewrite as coffee-talk (this is what you commit)

Rewrite from the mechanism — not from the wording of the draft. Copying-then-polishing preserves jargon.

Follow the rules in "Idea Description Rules" above: 2–3 sentences, concrete example mandatory, first sentence states what the idea IS.

Before committing, apply the reader test:
- If the reader has only this description and nothing else — no session, no frame, no parent idea, no hint — can they understand it?
- Does the first sentence state the idea, rather than narrate how you arrived at it?

If either fails, rewrite.

## Required Idea Fields

Every row inserted into the `ideas` table must carry at minimum:

| Column | What to Write | Example |
|--------|--------------|---------|
| `title` | Short name, 3–80 characters, no numbering or prefixes | `Anonymized task posting` |
| `description` | 2-3 sentences, coffee-talk style with a concrete example | "Companies post tasks stripped of their name. A freelancer sees 'analyze Q3 revenue for a mid-size SaaS company' instead of 'analyze Stripe's Q3 numbers.'" |
| `kind` | One of `seed`, `variant`, `hybrid`, `refinement`, `counter` | `seed` for a specialist's raw output; `variant` for a SCAMPER/invert/cross-domain child; `hybrid` for a multi-parent combination; `refinement` for a revision of one parent; `counter` for a deliberately opposed idea |
| `tag` | `SAFE`, `BOLD`, or `WILD` — or omit for framing-stage outputs | `WILD` |
| `temperature_zone` | `FIRE`, `PLASMA`, `ICE`, `GHOST`, or `MIRROR` — only set by operators invoked with a zone parameter | `FIRE` |

Pros, cons, and prerequisites are not columns on `ideas`. They are recorded as assessments — use metrics `pros`, `cons`, `requires` (one row per claim) so that richer lists and contradictions are queryable. See `ideation.logbook.md` for the assessment schema.

**BAD — jargon-laden advantages:**
"TAM expansion via network effects and viral coefficient optimization."

**GOOD — coffee-talk advantage with example:**
"Existing users bring their colleagues without you lifting a finger — like how Slack spread through one team and quietly took over a company."

Write all assessments with the same coffee-talk discipline as descriptions.

## Idea Menu Buckets

`decide.export(format=menu)` assigns a bucket per shortlisted idea based on qualitative judgment, not numeric thresholds. Most ideas stay unbucketed.

| Bucket | Qualitative definition | Action |
|--------|------------------------|--------|
| **Quick Wins** | Can be started immediately with existing resources; low structural risk | Do these first |
| **Core Bets** | Main strategic plays addressing the session's deepest root cause | Commit to these after stress-testing |
| **Moonshots** | High-novelty, high-upside; requires proof search before commitment | Validate with proof searches first |

Buckets are stored as assessments with `metric='menu_bucket'` and `value` of `quick_win` / `core_bet` / `moonshot`. Assign sparingly (3-5 per bucket maximum).

## What NOT to Include in Converge Output

When presenting final selected ideas via `decide.converge`, do **not** include:

- Implementation timeline estimates ("6-week MVP", "build in 3 months", "ship in Q2")
- Action plan schedules ("Week 1: do X, Week 2: do Y")
- "90-day success metrics" or "first-action" checklists

These estimates are invented — the agent has no knowledge of team size, stack, prior work, or scope. Presenting them as concrete outputs creates false confidence and wastes the reader's attention. Focus instead on each idea's mechanism, why it fits the problem, and what assumptions need validating. The user decides their own timelines.

## No Scores or Formulas in User-Facing Output

Do not show raw scores, composite scores, weighted formulas, or assessment numerics in any text the user reads directly — including the Idea Menu, Converge output, and Brilliance summaries.

Scores are used internally to rank and filter ideas. The output of that ranking is the bucket the idea lands in (Quick Win / Core Bet / Moonshot) and the prose explanation of why. A reader should never have to interpret a number to understand what to do.

**BAD:** "Idea #42: ICE=8.4, composite=7.6 — recommended."
**GOOD:** "This is a Quick Win. It's fast to test and you already have the distribution."

## No Methodology Names in User-Facing Text

Do not mention TRIZ, SCAMPER, Six Thinking Hats, Disney Spiral, temperature zones, Synectics, or any other internal framework name in any text the user reads.

These names are instructions for how agents generate ideas — not explanations of the ideas themselves. Mentioning them adds noise and signals process over substance.

If the mechanism of an idea came from inverting a constraint, just describe the inversion: "What if instead of X, you did the opposite — Y?" The user doesn't need to know what it was called.

## Batch writes — mandatory for any high-volume operator

If your operator will write **more than ~5 rows** of the same kind (ideas, facts, lineage edges, assessments, or idea patches) in a single run, use the batch CLI commands. Calling `add-assessment` 200 times in a loop spawns 200 subprocesses, each paying Python startup + SQLite connection overhead. The batch endpoints do one subprocess and one transaction.

| Row kind | Batch command |
|---|---|
| ideas | `ideation_db.py add-ideas-batch <slug> <json-file> --origin-operator-run-id <N>` |
| facts | `ideation_db.py add-facts-batch <slug> <json-file> --operator-run-id <N>` |
| lineage edges | `ideation_db.py add-lineage-batch <slug> <json-file> --operator-run-id <N>` |
| assessments | `ideation_db.py add-assessments-batch <slug> <json-file> --operator-run-id <N>` |
| idea mutable-field patches | `ideation_db.py patch-ideas-batch <slug> <json-file>` |

**Pattern to follow:** collect all rows into a local data structure, serialise to a tempfile (e.g. `/tmp/<operator>-$OPERATOR_RUN_ID.json`), run the batch command, then remove the tempfile. Do this even if the code feels more elegant with a loop — the performance difference is the whole cost of your operator.

**Operators that must batch:** `evaluate.score`, `evaluate.hats`, `evaluate.brilliance`, `evaluate.tension`, `evaluate.taste_check` (if the cohort exceeds one `AskUserQuestion` round), `validate.web_stress`, `decide.shortlist` (when patching > 5 statuses), and any `generate.*` / `transform.*` operator that produces more than 5 ideas.

## ID Discipline

All operators must reference ideas by their `idea_id` — the auto-increment integer PK in the `ideas` table.

- **Canonical format:** `idea #47`
- **With alias:** `idea #47 (alias: "Narrative Loading")` — informal labels allowed only as parenthetical aliases
- **Downstream operators must key off the integer ID**, not the alias — title text is not stable across refinement

In outcome summaries and report artifacts, every idea reference must include its integer ID. If you refer to an idea by title, always include `(#47)` after it.
