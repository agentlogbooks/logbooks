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

    def test_lint_operators_aggregates_multiple_lint_errors(self):
        bad1 = VALID_OP_FILE.replace("stage: transform", "stage: decide")
        bad2 = VALID_OP_FILE.replace(
            "name: transform.invert", "name: transform.hybridize"
        ).replace("scope: per_idea", "scope: broken_scope_value")
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text(bad1)
            (ops / "transform.hybridize.md").write_text(bad2)
            result = _run_cli("lint-operators", operators_dir=ops)
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("transform.invert.md", output)
        self.assertIn("transform.hybridize.md", output)
        # Both files must be reported — a fail-fast impl would only show one.

    def test_lint_operators_aggregates_parse_and_lint_errors(self):
        bad_lint = VALID_OP_FILE.replace("stage: transform", "stage: decide")
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text(bad_lint)
            (ops / "transform.hybridize.md").write_text("no frontmatter here\n")
            result = _run_cli("lint-operators", operators_dir=ops)
        self.assertNotEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("transform.invert.md", output)
        self.assertIn("transform.hybridize.md", output)
        self.assertIn("frontmatter", output.lower())

    def test_lint_operators_handles_binary_files_gracefully(self):
        with tempfile.TemporaryDirectory() as td:
            ops = Path(td) / "operators"
            ops.mkdir()
            (ops / "transform.invert.md").write_text(VALID_OP_FILE)
            # Write invalid UTF-8 bytes to a .md file.
            (ops / "broken.md").write_bytes(b"\xff\xfe\xfd not utf-8 \xc3\x28")
            result = _run_cli("lint-operators", operators_dir=ops)
        # Should not crash; should report the read error for the bad file.
        output = result.stdout + result.stderr
        self.assertIn("broken.md", output)
        # The clean file should still have been processed.


if __name__ == "__main__":
    unittest.main()
