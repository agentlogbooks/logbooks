import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

from operator_meta import (  # noqa: E402
    parse_frontmatter,
    lint_operator,
    load_catalog,
    FrontmatterError,
    LintError,
    VALID_STAGES,
    VALID_SCOPES,
    VALID_KINDS,
)


VALID_FRONTMATTER = """---
name: transform.invert
stage: transform
scope: per_idea
applies_to:
  kinds: [seed, variant, hybrid]
  min_cohort: 1
use_when:
  - promising but brittle
  - obvious objections or failure modes
avoid_when:
  - already inverted recently on this lineage
  - idea too vague to invert meaningfully
produces:
  ideas: true
  assessments: false
  facts: false
cost:
  web: false
repeat_guard:
  same_lineage_cooldown: 1
followups:
  - transform.refine
  - validate.proof_search
---

# Operator: transform.invert

body goes here.
"""


class TestParseFrontmatterValid(unittest.TestCase):
    def test_parses_all_required_fields(self):
        meta = parse_frontmatter(VALID_FRONTMATTER)
        self.assertEqual(meta["name"], "transform.invert")
        self.assertEqual(meta["stage"], "transform")
        self.assertEqual(meta["scope"], "per_idea")
        self.assertEqual(meta["applies_to"]["kinds"], ["seed", "variant", "hybrid"])
        self.assertEqual(meta["applies_to"]["min_cohort"], 1)
        self.assertEqual(
            meta["use_when"],
            ["promising but brittle", "obvious objections or failure modes"],
        )
        self.assertEqual(
            meta["avoid_when"],
            [
                "already inverted recently on this lineage",
                "idea too vague to invert meaningfully",
            ],
        )
        self.assertEqual(meta["produces"], {"ideas": True, "assessments": False, "facts": False})
        self.assertEqual(meta["cost"], {"web": False})
        self.assertEqual(meta["repeat_guard"], {"same_lineage_cooldown": 1})
        self.assertEqual(meta["followups"], ["transform.refine", "validate.proof_search"])


class TestParseFrontmatterRejects(unittest.TestCase):
    def test_rejects_missing_open_fence(self):
        text = "name: foo\n---\n\n# body\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_rejects_missing_close_fence(self):
        text = "---\nname: foo\n\n# body\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_rejects_no_frontmatter_at_all(self):
        text = "# Operator: foo\n\nbody\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_rejects_bad_indentation(self):
        text = "---\nfoo: bar\n   baz: qux\n---\n\nbody\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_parses_inline_empty_list(self):
        text = "---\napplies_to:\n  kinds: []\n  min_cohort: 1\n---\n\nbody\n"
        meta = parse_frontmatter(text)
        self.assertEqual(meta["applies_to"]["kinds"], [])
        self.assertEqual(meta["applies_to"]["min_cohort"], 1)


class TestParseFrontmatterStrictGrammar(unittest.TestCase):
    def test_rejects_tab_indented_child(self):
        # single tab in place of 2-space indent
        text = "---\nfoo:\n\tbar: baz\n---\n\nbody\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_rejects_duplicate_top_level_key(self):
        text = "---\nname: foo\nname: bar\n---\n\nbody\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)

    def test_rejects_empty_key(self):
        text = "---\n: value\n---\n\nbody\n"
        with self.assertRaises(FrontmatterError):
            parse_frontmatter(text)


def _meta(**overrides):
    """Build a minimal valid meta dict; override to break specific rules."""
    base = {
        "name": "transform.invert",
        "stage": "transform",
        "scope": "per_idea",
        "applies_to": {"kinds": ["seed", "variant", "hybrid"], "min_cohort": 1},
        "use_when": ["a"],
        "avoid_when": ["b"],
        "produces": {"ideas": True, "assessments": False, "facts": False},
        "cost": {"web": False},
        "repeat_guard": {"same_lineage_cooldown": 1},
        "followups": [],
    }
    for k, v in overrides.items():
        base[k] = v
    return base


class TestLintOperator(unittest.TestCase):
    def test_valid_meta_returns_no_errors(self):
        errs = lint_operator(_meta(), filename="transform.invert.md")
        self.assertEqual(errs, [])

    def test_missing_required_field_fails(self):
        meta = _meta()
        del meta["use_when"]
        errs = lint_operator(meta, filename="transform.invert.md")
        self.assertTrue(any("use_when" in e for e in errs))

    def test_name_must_match_filename(self):
        errs = lint_operator(_meta(), filename="transform.hybridize.md")
        self.assertTrue(any("filename" in e.lower() for e in errs))

    def test_stage_must_match_name_prefix(self):
        errs = lint_operator(_meta(stage="decide"), filename="transform.invert.md")
        self.assertTrue(any("stage" in e.lower() for e in errs))

    def test_scope_must_be_in_enum(self):
        errs = lint_operator(_meta(scope="global"), filename="transform.invert.md")
        self.assertTrue(any("scope" in e.lower() for e in errs))

    def test_applies_to_kinds_must_be_valid(self):
        errs = lint_operator(
            _meta(applies_to={"kinds": ["fictional"], "min_cohort": 1}),
            filename="transform.invert.md",
        )
        self.assertTrue(any("kinds" in e.lower() for e in errs))

    def test_transform_must_produce_ideas(self):
        errs = lint_operator(
            _meta(produces={"ideas": False, "assessments": False, "facts": False}),
            filename="transform.invert.md",
        )
        self.assertTrue(any("produces.ideas" in e for e in errs))

    def test_validate_must_produce_facts_and_assessments(self):
        errs = lint_operator(
            _meta(
                name="validate.web_stress",
                stage="validate",
                produces={"ideas": False, "assessments": False, "facts": False},
            ),
            filename="validate.web_stress.md",
        )
        self.assertTrue(any("facts" in e for e in errs))
        self.assertTrue(any("assessments" in e for e in errs))

    def test_evaluate_must_produce_assessments(self):
        errs = lint_operator(
            _meta(
                name="evaluate.tension",
                stage="evaluate",
                produces={"ideas": False, "assessments": False, "facts": False},
            ),
            filename="evaluate.tension.md",
        )
        self.assertTrue(any("assessments" in e for e in errs))

    def test_frame_must_not_produce_ideas(self):
        errs = lint_operator(
            _meta(
                name="frame.discover",
                stage="frame",
                produces={"ideas": True, "assessments": False, "facts": False},
            ),
            filename="frame.discover.md",
        )
        self.assertTrue(any("frame" in e.lower() and "ideas" in e.lower() for e in errs))

    def test_pool_scope_must_have_zero_cooldown(self):
        errs = lint_operator(
            _meta(
                scope="pool",
                repeat_guard={"same_lineage_cooldown": 3},
                applies_to={"kinds": [], "min_cohort": 1},
            ),
            filename="transform.invert.md",
        )
        self.assertTrue(any("cooldown" in e.lower() for e in errs))

    def test_followups_must_exist_in_catalog(self):
        errs = lint_operator(
            _meta(followups=["transform.refine", "nonexistent.op"]),
            filename="transform.invert.md",
            known_operator_names={"transform.refine", "transform.invert"},
        )
        self.assertTrue(any("nonexistent.op" in e for e in errs))

    def test_followups_skip_when_known_names_is_none(self):
        errs = lint_operator(
            _meta(followups=["nonexistent.op"]),
            filename="transform.invert.md",
            known_operator_names=None,
        )
        self.assertEqual(errs, [])

    def test_min_cohort_zero_fails(self):
        errs = lint_operator(
            _meta(applies_to={"kinds": ["seed"], "min_cohort": 0}),
            filename="transform.invert.md",
        )
        self.assertTrue(any("min_cohort" in e for e in errs))

    def test_same_lineage_cooldown_negative_fails(self):
        errs = lint_operator(
            _meta(repeat_guard={"same_lineage_cooldown": -1}),
            filename="transform.invert.md",
        )
        self.assertTrue(any("cooldown" in e.lower() for e in errs))

    def test_cost_web_must_be_bool(self):
        errs = lint_operator(
            _meta(cost={"web": "false"}),
            filename="transform.invert.md",
        )
        self.assertTrue(any("cost" in e.lower() for e in errs))

    def test_multiple_errors_accumulate(self):
        errs = lint_operator(
            _meta(
                name="decide.export",
                stage="transform",
                scope="global",
            ),
            filename="transform.invert.md",
        )
        # Three distinct rule violations expected
        self.assertTrue(any("filename" in e.lower() for e in errs))
        self.assertTrue(any("stage" in e.lower() for e in errs))
        self.assertTrue(any("scope" in e.lower() for e in errs))


if __name__ == "__main__":
    unittest.main()
