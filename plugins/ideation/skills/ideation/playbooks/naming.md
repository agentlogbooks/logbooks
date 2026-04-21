# Playbook: naming

Generate, filter, and validate names for a product, feature, company, project, or anything else. Naming is a distinct craft — AI struggles with it because the failure modes are specific (collisions, weak phonetics, off-tone, too clever) and good names hide in volume. This playbook generates ~70 candidates from five naming angles, lets the user taste-pick survivors, then validates the shortlist with web research.

## When to pick

- User asks to "name", "rename", "come up with a name for", "find a name", "brand", "title" something.
- Matches intent shape: `"name <thing>"`, `"naming ideas for <thing>"`, `"what should we call <thing>"`, `"rebrand <thing>"`.
- The topic is specifically about picking a name — not ideating a product that will later need a name.

## When NOT to pick

- The user wants product ideas, not names — use `starter` or `deep_explore`.
- The user already has a shortlist of 3-5 names and just wants validation — use `stress_test_shortlist` on those IDs directly.
- The user wants to rename something inside a codebase (variables, APIs) — naming usually means brand/product naming; narrow technical renames rarely benefit from this much ceremony.

## Steps

1. Capture the naming brief: what's being named, tone, audience, constraints (frame.discover)
2. ⏸ Checkpoint — confirm the naming brief before generating
3. Generate ~70 candidate names from five angles in parallel:
   - Descriptive names — 15 (generate.seed persona=namer count=15 emphasis="descriptive — plain words describing what the thing does")
   - Metaphorical names — 15 (generate.seed persona=namer count=15 emphasis="metaphors from nature, mythology, concrete objects, and animals")
   - Portmanteau names — 10 (generate.seed persona=namer count=10 emphasis="blend two words relevant to the brief into one new word")
   - Invented / phonetic names — 15 (generate.seed persona=namer count=15 emphasis="invented words chosen for sound and suggestion, not meaning")
   - Classical-root names — 10 (generate.seed persona=namer count=10 emphasis="Latin, Greek, or Sanskrit roots with meanings tied to the brief")
4. ⏸ Checkpoint — taste check: pick ~10 favorites from the full batch (evaluate.taste_check)
5. Validate the survivors via web research — check domain availability, trademark collisions, and whether the name is already taken in the category (validate.web_stress cohort=top-by-metric(metric=taste, n=10))
6. Compare the validated survivors side-by-side with evidence (decide.compare cohort=top-by-metric(metric=taste, n=10))

## Expected output

- One frame row capturing the naming brief (what, tone, audience, constraints).
- ~70 name candidates in the logbook, distributed across SAFE / BOLD / WILD and five naming angles.
- ~10 taste-picked favorites with `taste=picked` assessments.
- Web-sourced facts on the top 10: domain availability observations, trademark hits, similar brands in the category. Evidence-state on each shifts from `untested` to `supported` / `stressed` / `disputed`.
- One comparison report under `./.ideation/<slug>/reports/<run_id>-compare.md` showing name, description, taste rank, and a one-line evidence summary for each survivor.

## Notes on the craft

- **Volume matters.** The winning name frequently appears in the 30-60 range. Five parallel generations × 10-15 each produces the volume in one fan-out without dragging the user through rounds.
- **No formal scoring.** Naming quality is perceptual — memorability, sayability, vibe — and formal 1-5 scoring on abstract criteria often generates false precision. `evaluate.taste_check` (binary pick/not) is the right evaluation for names.
- **Web validation is non-negotiable.** Unlike idea evaluation where web-stress is optional, naming without a domain/trademark check is irresponsible — the first thing a reader does with a name is google it. `validate.web_stress` searches each candidate for: existing products in adjacent categories, trademark registrations, common-noun SEO burial (e.g., "Patch" is memorable but un-searchable), and domain root availability (without buying — that's the user's call).
- **The namer persona encodes the craft.** See `references/personas/namer.md` for the voice, angles, and failure modes. The playbook injects a different `emphasis` hint into each of the five parallel `generate.seed` calls so each batch leans into one angle.

## Follow-ups

- **Deeper validation on the final 3**: `ideation <slug>: stress-test the top 3 names` runs `validate.web_stress` with more rigor on the survivors.
- **A variant pass on a specific name**: `ideation <slug>: develop name N further` uses `followup_develop` to produce variants (spelling tweaks, stem extensions, truncations) around a specific candidate.
- **Complete reframe**: if none of the 70 survivors feel right, `ideation <slug>: the brief was wrong — it's actually for <X>` runs `reframe_and_regenerate` under a new naming brief.
