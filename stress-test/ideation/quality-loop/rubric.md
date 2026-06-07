# Idea-output quality rubric (grounded in output-rules.md)

Score every idea 1–5 on each dimension. The two groups are reported **separately**
— never blended — because they fail differently (see note at bottom).

## Compliance (cheap to lift by editing the prompt — low information on its own)

- **C1 coffee_talk** — 2–3 sentences, self-contained; a reader with zero context
  (no frame, no session) understands it. (output-rules.md "Idea Description Rules")
- **C2 concrete_example** — a specific who-does-what-with-what example is present, not
  a slogan. (output-rules.md "Example is mandatory")
- **C3 no_jargon** — no methodology names (SCAMPER/TRIZ/etc.), no "Week 1"/formulas/
  internal terms, no narration of how it was generated. (output-rules.md "No
  Methodology Names", "BAD — procedural/abstract")

## Substance (the real prize — hard to fake by teaching-to-rubric — WATCH THIS)

- **S1 novelty** — non-obvious; not the first thing anyone would say about the problem.
- **S2 mechanism_specificity** — names a concrete, plausible mechanism (who does what,
  what changes), not a vague direction ("make it modular", "improve engagement").
- **S3 relevance** — actually attacks a root cause / HMW in the frame, not a generic move.

## Batch-level (scored once per (topic, persona) set, 1–5)

- **S4 diversity** — the set spans distinct mechanisms (not all the same move) and a
  healthy tag spread (SAFE/BOLD/WILD), per generate.seed.md "Distinct mechanisms".

## Aggregation

- `compliance = mean(C1, C2, C3)` averaged over all ideas.
- `substance  = mean(S1, S2, S3)` averaged over all ideas, then averaged with the
  batch-level S4 means.
- Report compliance and substance as two separate numbers per round.

## Why split

Compliance is trivially liftable — the improver just adds "ALWAYS include an example",
and C2 jumps. That is high movement, low information. Substance is what we actually
want and is resistant to teaching-to-rubric. **A compliance jump masquerading as
"idea quality improved" is the failure mode of this whole loop.** The honest result is
the end-of-loop BLIND A/B (round-1 vs round-5, labels stripped, fresh judge): if
substance does not beat round-1 blind, the prompt tuning did not move real quality —
and that is a valid, reportable finding.
