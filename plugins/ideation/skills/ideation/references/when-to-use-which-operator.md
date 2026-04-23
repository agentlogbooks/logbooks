<!--
This file is generated from operator frontmatter.
Regenerate with: `python plugins/ideation/skills/ideation/scripts/ideation_db.py generate-reference`
Do not edit by hand — your changes will be overwritten.
-->

# When to use which operator

Generated from operator frontmatter. Grouped by stage. For each operator, the **scope** line tells the router how it consumes ideas; **Use when** and **Avoid when** are the judgment cues.

## Frame operators

### frame.context_scout

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - problem needs external grounding facts before framing
  - user asks for "thorough" or "deep" framing
- **Avoid when:**
  - topic is already framed and facts have been gathered
- **Typical followups:** frame.discover

### frame.discover

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - no active frame exists
  - topic needs root causes, HMW, trade-off surfaced
- **Avoid when:**
  - active frame already covers the problem
- **Typical followups:** generate.seed, frame.context_scout

### frame.historian

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - prior attempts exist and their lessons are relevant
  - user references "what did we try before"
- **Avoid when:**
  - no prior history to surface
- **Typical followups:** frame.discover

### frame.reframe

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - existing frame feels wrong — root causes miss the point
  - user explicitly asks to reframe
- **Avoid when:**
  - no prior frame (use frame.discover)
- **Typical followups:** generate.seed

## Generate operators

### generate.fresh

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - user gives a concrete hint and wants ideas shaped around it
  - prior seeds are stale and a hint-driven reset is warranted
- **Avoid when:**
  - no clear hint — use generate.seed with a persona instead
- **Typical followups:** transform.refine, evaluate.taste_check

### generate.seed

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - pool is empty or needs a fresh persona injection
  - user asks for a specific persona's take
- **Avoid when:**
  - pool is already saturated with seeds — transform or evaluate instead
- **Typical followups:** evaluate.taste_check, decide.compare

## Transform operators

### transform.cross_domain

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid
- **min cohort:** 1
- **Use when:**
  - idea feels generic or on-domain
  - analogies from other domains have not been explored yet
- **Avoid when:**
  - already cross-domained recently on this lineage
  - cohort is too large (run per-idea, not pool-wide)
- **Typical followups:** transform.refine, transform.hybridize

### transform.hybridize

- **scope:** group
- **applies to kinds:** seed, variant, hybrid
- **min cohort:** 2
- **Use when:**
  - two or three ideas have complementary mechanisms
  - a tension cluster wants synthesis
  - FIRE and ICE ideas could combine ambition with ship-ability
- **Avoid when:**
  - only one idea in the cohort
  - candidates are near-duplicates (hybridizing adds nothing)
  - already hybridized recently on this lineage
- **Typical followups:** transform.refine, validate.proof_search

### transform.invert

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid
- **min cohort:** 1
- **Use when:**
  - promising but brittle
  - obvious objections or failure modes
  - assumptions look too cautious
- **Avoid when:**
  - already inverted recently on this lineage
  - idea too vague to invert meaningfully
- **Typical followups:** transform.refine, validate.proof_search

### transform.john

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid
- **min cohort:** 1
- **Use when:**
  - seed needs to be pushed to a specific temperature zone
  - want a dreamer/realist/critic pass on this idea
- **Avoid when:**
  - already johned recently on this lineage
  - required zone/stance context is missing
- **Typical followups:** transform.ratchet, evaluate.taste_check

### transform.ratchet

- **scope:** group
- **applies to kinds:** seed, variant, hybrid
- **min cohort:** 2
- **Use when:**
  - tension cluster surfaced by evaluate.tension wants synthesis
  - a small hot shortlist needs cross-idea pressure
- **Avoid when:**
  - already ratcheted recently on this lineage
  - cohort is a single idea — use transform.refine
- **Typical followups:** evaluate.brilliance, decide.compare

### transform.refine

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid, refinement
- **min cohort:** 1
- **Use when:**
  - idea is strong but the mechanism is vague
  - user supplied a specific hint to apply
  - prior pass left open questions on this idea
- **Avoid when:**
  - already refined twice on this lineage
  - idea is not yet stable enough to specify
- **Typical followups:** validate.proof_search, validate.web_stress

### transform.scamper

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid, refinement
- **min cohort:** 1
- **Use when:**
  - a seed feels underdeveloped and structured mutation helps
  - the user names "develop", "expand", or "build on" an idea
- **Avoid when:**
  - already SCAMPERed recently on this lineage
  - idea is highly abstract — transforms need a concrete mechanism to flex
- **Typical followups:** transform.refine, evaluate.taste_check

## Evaluate operators

### evaluate.brilliance

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid, refinement
- **min cohort:** 1
- **Use when:**
  - an idea is shortlist-worthy but its signal is unclear
  - user asks "what's actually brilliant here"
- **Avoid when:**
  - already brilliance-checked recently on this lineage
- **Typical followups:** decide.converge

### evaluate.criteria

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - pool is ready for ranking but criteria are not yet locked
  - user asks to "score" or "prioritize"
- **Avoid when:**
  - criteria already locked for this session
- **Typical followups:** evaluate.score

### evaluate.hats

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid, refinement
- **min cohort:** 1
- **Use when:**
  - an idea wants a multi-perspective pass before deciding
  - emotional, data, and process angles are all missing
- **Avoid when:**
  - already hat-evaluated recently on this lineage
- **Typical followups:** transform.refine, decide.compare

### evaluate.score

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - criteria are locked and ideas need composite scores
  - user wants ranking before converge
- **Avoid when:**
  - no criteria yet (run evaluate.criteria first)
- **Typical followups:** decide.shortlist, decide.compare

### evaluate.taste_check

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 2
- **Use when:**
  - a batch of seeds or variants needs a user-taste filter
  - upcoming step will narrow the pool (before converge/score)
- **Avoid when:**
  - pool is tiny (fewer than 2 ideas)
- **Typical followups:** decide.shortlist, evaluate.score

### evaluate.tension

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 3
- **Use when:**
  - the pool has multiple ideas and internal conflicts are not yet visible
  - you want to surface candidate pairs for hybridize
- **Avoid when:**
  - pool has fewer than 3 ideas
- **Typical followups:** transform.hybridize, transform.ratchet

## Validate operators

### validate.proof_search

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid, refinement
- **min cohort:** 1
- **Use when:**
  - idea makes a claim that wants supporting evidence
  - user asks "does this exist elsewhere" or "has this been tried"
- **Avoid when:**
  - already proof-searched recently on this lineage
  - params.cheap is set
- **Typical followups:** decide.converge

### validate.web_stress

- **scope:** per_idea
- **applies to kinds:** seed, variant, hybrid, refinement
- **min cohort:** 1
- **Use when:**
  - idea is strong on its own but lacks external evidence
  - user asks for "stress test" or "validate"
- **Avoid when:**
  - already stress-tested recently on this lineage
  - params.cheap is set
- **Typical followups:** decide.converge

## Decide operators

### decide.compare

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 2
- **Use when:**
  - user wants side-by-side readout of a cohort
  - after generate or transform bursts
- **Avoid when:**
  - single idea (no comparison possible)
- **Typical followups:** decide.shortlist, decide.converge

### decide.converge

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 2
- **Use when:**
  - pool has been evaluated and validated
  - user asks to "pick" or "decide" or "converge"
- **Avoid when:**
  - evaluation incomplete (no scores)
- **Typical followups:** decide.export

### decide.export

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - pool has selected ideas ready to leave the skill
  - user asks for "menu" or "export"
- **Avoid when:**
  - nothing selected yet

### decide.route

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 1
- **Use when:**
  - pool has a mix of idea states and next moves are not obvious
  - mid-flow decision on what to do with each of a batch of ideas
- **Avoid when:**
  - pool is too small to warrant routing (fewer than 5 ideas)
  - intent is a single-shape bulk operation (use the direct playbook instead)

### decide.shortlist

- **scope:** pool
- **applies to kinds:** —
- **min cohort:** 2
- **Use when:**
  - evaluation is complete and a narrowing step is needed
  - user asks for "top N" or "best few"
- **Avoid when:**
  - no scores or taste signals available yet
- **Typical followups:** decide.compare, decide.converge
