import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
IDEATION_DB = SCRIPTS / "ideation_db.py"


def _run_cli(*args, operators_dir: Path | None = None) -> subprocess.CompletedProcess:
    env = None
    if operators_dir is not None:
        import os
        env = os.environ.copy()
        env["IDEATION_OPERATORS_DIR"] = str(operators_dir)
    return subprocess.run(
        [sys.executable, str(IDEATION_DB), *args],
        capture_output=True,
        text=True,
        env=env,
    )


VALID_OP_FILE = textwrap.dedent(
    """\
    ---
    name: transform.invert
    stage: transform
    scope: per_idea
    applies_to:
      kinds: [seed, variant, hybrid]
      min_cohort: 1
    use_when:
      - promising but brittle
    avoid_when:
      - already inverted recently on this lineage
    produces:
      ideas: true
      assessments: false
      facts: false
    cost:
      web: false
    repeat_guard:
      same_lineage_cooldown: 1
    followups: []
    ---

    # Operator: transform.invert

    body.
    """
)


class TestListOperatorsCli(unittest.TestCase):
    def test_list_operators_emits_json_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text(VALID_OP_FILE)
            result = _run_cli("list-operators", "--format", "json", operators_dir=ops)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(len(payload["operators"]), 1)
        self.assertEqual(payload["operators"][0]["name"], "transform.invert")

        # Structural contract for decide.route — the catalog shape is part of the API.
        entry = payload["operators"][0]
        required = {
            "name", "stage", "scope", "applies_to", "use_when",
            "avoid_when", "produces", "cost", "repeat_guard", "followups",
        }
        self.assertEqual(set(entry.keys()), required)
        self.assertIsInstance(entry["applies_to"]["min_cohort"], int)
        self.assertIsInstance(entry["produces"]["ideas"], bool)
        self.assertIsInstance(entry["cost"]["web"], bool)
        self.assertIsInstance(entry["repeat_guard"]["same_lineage_cooldown"], int)
        self.assertIsInstance(entry["use_when"], list)
        self.assertIsInstance(entry["avoid_when"], list)
        self.assertIsInstance(entry["followups"], list)

    def test_list_operators_fails_when_frontmatter_missing(self):
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text("# Operator: transform.invert\n\nno frontmatter.\n")
            result = _run_cli("list-operators", operators_dir=ops)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("transform.invert.md", result.stderr)

    def test_list_operators_fails_when_lint_fails(self):
        bad = VALID_OP_FILE.replace("stage: transform", "stage: decide")
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text(bad)
            result = _run_cli("list-operators", operators_dir=ops)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stage", result.stderr.lower())


class TestLintOperatorsCli(unittest.TestCase):
    def test_lint_operators_passes_on_clean_catalog(self):
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text(VALID_OP_FILE)
            result = _run_cli("lint-operators", operators_dir=ops)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("0 errors", result.stdout)

    def test_lint_operators_fails_on_bad_stage(self):
        bad = VALID_OP_FILE.replace("stage: transform", "stage: decide")
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text(bad)
            result = _run_cli("lint-operators", operators_dir=ops)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("transform.invert.md", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
