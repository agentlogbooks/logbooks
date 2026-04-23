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


if __name__ == "__main__":
    unittest.main()
