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


class TestAllActiveCapped(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.env = os.environ.copy()
        self.env["IDEATION_ROOT_OVERRIDE"] = self.td.name
        self.slug = "test"
        _cli(self.env, "init-topic", self.slug, "--description", "t", "--owner", "t")
        rid = _cli(self.env, "new-run-id").stdout.strip()
        op1 = _cli(
            self.env, "op-start", self.slug,
            "--run-id", rid,
            "--operator", "frame.discover",
            "--cohort-ids-json", "[]",
        ).stdout.strip()
        _cli(self.env, "op-finalize", self.slug, op1,
             "--status", "succeeded", "--outcome-summary", "ok")
        _cli(
            self.env, "add-frame", self.slug,
            "--problem-statement", "p",
            "--root-causes-json", json.dumps(["a"]),
            "--hmw-questions-json", json.dumps(["q?"]),
            "--operator-run-id", op1,
        )
        op2 = _cli(
            self.env, "op-start", self.slug,
            "--run-id", rid,
            "--operator", "generate.seed",
            "--cohort-ids-json", "[]",
        ).stdout.strip()
        _cli(self.env, "op-finalize", self.slug, op2,
             "--status", "succeeded", "--outcome-summary", "ok")
        self.ids = []
        for i in range(7):
            out = _cli(
                self.env, "add-idea", self.slug,
                "--title", f"idea {i}", "--description", "d", "--kind", "seed",
                "--origin-operator-run-id", op2,
            ).stdout.strip()
            self.ids.append(int(out))

    def tearDown(self):
        self.td.cleanup()

    def test_caps_to_n(self):
        r = _cli(self.env, "query", self.slug, "all-active-capped", "--n", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        ids = json.loads(r.stdout)
        self.assertEqual(ids, self.ids[:3])

    def test_returns_all_when_n_exceeds_pool(self):
        r = _cli(self.env, "query", self.slug, "all-active-capped", "--n", "50")
        ids = json.loads(r.stdout)
        self.assertEqual(ids, self.ids)

    def test_is_deterministic_across_calls(self):
        a = json.loads(_cli(self.env, "query", self.slug, "all-active-capped", "--n", "5").stdout)
        b = json.loads(_cli(self.env, "query", self.slug, "all-active-capped", "--n", "5").stdout)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
