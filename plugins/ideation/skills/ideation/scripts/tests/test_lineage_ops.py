import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
IDEATION_DB = SCRIPTS / "ideation_db.py"


def _cli(env, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(IDEATION_DB), *args],
        capture_output=True,
        text=True,
        env=env,
    )


class TestLineageOpsCli(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.env = os.environ.copy()
        self.env["IDEATION_ROOT_OVERRIDE"] = self.td.name
        self.slug = "test"
        # init
        r = _cli(self.env, "init-topic", self.slug, "--description", "t", "--owner", "t")
        self.assertEqual(r.returncode, 0, r.stderr)
        # run_id
        rid = _cli(self.env, "new-run-id").stdout.strip()
        self.rid = rid
        # a framing op run (required to add a frame)
        op1 = _cli(
            self.env, "op-start", self.slug,
            "--run-id", rid,
            "--operator", "frame.discover",
            "--cohort-ids-json", "[]",
        ).stdout.strip()
        _cli(
            self.env, "op-finalize", self.slug, op1,
            "--status", "succeeded", "--outcome-summary", "ok",
        )
        # a frame
        _cli(
            self.env, "add-frame", self.slug,
            "--problem-statement", "p",
            "--root-causes-json", json.dumps(["a"]),
            "--hmw-questions-json", json.dumps(["q?"]),
            "--operator-run-id", op1,
        )
        # two operator runs creating ideas
        self.op_invert = _cli(
            self.env, "op-start", self.slug,
            "--run-id", rid,
            "--operator", "transform.invert",
            "--cohort-ids-json", "[]",
        ).stdout.strip()
        _cli(
            self.env, "op-finalize", self.slug, self.op_invert,
            "--status", "succeeded", "--outcome-summary", "ok",
        )
        # parent idea
        self.parent_id = int(_cli(
            self.env, "add-idea", self.slug,
            "--title", "parent", "--description", "d", "--kind", "seed",
            "--origin-operator-run-id", self.op_invert,
        ).stdout.strip())
        # child idea linked to parent
        self.op_scamper = _cli(
            self.env, "op-start", self.slug,
            "--run-id", rid,
            "--operator", "transform.scamper",
            "--cohort-ids-json", f"[{self.parent_id}]",
        ).stdout.strip()
        _cli(
            self.env, "op-finalize", self.slug, self.op_scamper,
            "--status", "succeeded", "--outcome-summary", "ok",
        )
        self.child_id = int(_cli(
            self.env, "add-idea", self.slug,
            "--title", "child", "--description", "d", "--kind", "variant",
            "--origin-operator-run-id", self.op_scamper,
        ).stdout.strip())
        _cli(
            self.env, "add-lineage", self.slug,
            "--child", str(self.child_id), "--parent", str(self.parent_id),
            "--relation", "derived_from",
            "--operator-run-id", self.op_scamper,
        )

    def tearDown(self):
        self.td.cleanup()

    def test_lineage_ops_returns_ancestor_and_descendant_ops(self):
        r = _cli(self.env, "lineage-ops", self.slug, str(self.child_id), "--limit", "10")
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = json.loads(r.stdout)
        op_names = [row["operator_name"] for row in rows]
        self.assertIn("transform.invert", op_names)
        self.assertIn("transform.scamper", op_names)

    def test_lineage_ops_respects_limit(self):
        r = _cli(self.env, "lineage-ops", self.slug, str(self.child_id), "--limit", "1")
        rows = json.loads(r.stdout)
        self.assertEqual(len(rows), 1)

    def test_lineage_ops_includes_cohort_only_runs(self):
        """evaluate.* / validate.* runs read ideas via cohort_ids without writing
        to ideas or lineage. They still count for cooldown purposes."""
        op_hats = _cli(
            self.env, "op-start", self.slug,
            "--run-id", self.rid,
            "--operator", "evaluate.hats",
            "--cohort-ids-json", f"[{self.child_id}]",
        ).stdout.strip()
        _cli(
            self.env, "op-finalize", self.slug, op_hats,
            "--status", "succeeded", "--outcome-summary", "ok",
        )
        r = _cli(self.env, "lineage-ops", self.slug, str(self.child_id), "--limit", "10")
        rows = json.loads(r.stdout)
        op_names = [row["operator_name"] for row in rows]
        self.assertIn("evaluate.hats", op_names)


if __name__ == "__main__":
    unittest.main()
