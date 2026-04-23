#!/usr/bin/env python3
"""
ideation_db.py — SQLite multi-entity CLI for the ideation skill.

One database per topic at `./.ideation/<slug>/logbook.sqlite`.
Schema, semantics, and correction rules are documented in `ideation.logbook.md`.

Conventions:
- All timestamps are ISO 8601 UTC.
- JSON list columns (cohort_ids, root_causes, hmw_questions, evidence_fact_ids,
  triz_contradiction, params) are stored as JSON TEXT.
- Query commands print JSON arrays or JSON records to stdout for programmatic use.
- Mutation commands print the new row id (or "ok") to stdout.

Run `python ideation_db.py --help` for the command list.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ----------------------------------------------------------------------------
# Path resolution
# ----------------------------------------------------------------------------

IDEATION_DIR = ".ideation"


def _git_root(start: Path) -> Path | None:
    """Find the git repo root containing `start`, or None if not inside one."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except (FileNotFoundError, OSError):
        pass
    return None


def _ideation_root() -> Path:
    """Resolve the `./.ideation/` root: git repo root if inside one, else cwd."""
    cwd = Path.cwd().resolve()
    root = _git_root(cwd) or cwd
    return root / IDEATION_DIR


def _topic_dir(slug: str) -> Path:
    if not re.match(r"^[a-z0-9][a-z0-9_-]*$", slug):
        sys.exit(f"ERROR: invalid topic slug '{slug}' — use lowercase alphanum, dashes, underscores")
    return _ideation_root() / slug


def _logbook_path(slug: str) -> Path:
    return _topic_dir(slug) / "logbook.sqlite"


# ----------------------------------------------------------------------------
# Time helper
# ----------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ----------------------------------------------------------------------------
# DDL
# ----------------------------------------------------------------------------

DDL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS topic_meta (
  topic_slug TEXT PRIMARY KEY,
  description TEXT,
  owner TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operator_runs (
  operator_run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  plan_step_index INTEGER,
  operator_name TEXT NOT NULL,
  operator_persona TEXT,
  params TEXT,
  cohort_ids TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending','succeeded','failed','skipped')),
  outcome_summary TEXT,
  error TEXT,
  user_approved INTEGER NOT NULL CHECK (user_approved IN (0,1)),
  started_at TEXT NOT NULL,
  ended_at TEXT
);

CREATE TABLE IF NOT EXISTS frames (
  frame_id INTEGER PRIMARY KEY AUTOINCREMENT,
  version INTEGER NOT NULL,
  active INTEGER NOT NULL CHECK (active IN (0,1)),
  problem_statement TEXT NOT NULL,
  root_causes TEXT NOT NULL,
  hmw_questions TEXT NOT NULL,
  triz_contradiction TEXT,
  ifr_statement TEXT,
  supersedes_frame_id INTEGER REFERENCES frames(frame_id),
  operator_run_id INTEGER NOT NULL REFERENCES operator_runs(operator_run_id),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS facts (
  fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
  claim TEXT NOT NULL,
  source_url TEXT,
  source_label TEXT,
  confidence TEXT NOT NULL CHECK (confidence IN ('strong','medium','weak')),
  stance TEXT NOT NULL CHECK (stance IN ('supports','adversarial','neutral')),
  operator_run_id INTEGER NOT NULL REFERENCES operator_runs(operator_run_id),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ideas (
  idea_id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('seed','variant','hybrid','refinement','counter')),
  tag TEXT CHECK (tag IN ('SAFE','BOLD','WILD')),
  temperature_zone TEXT CHECK (temperature_zone IN ('FIRE','PLASMA','ICE','GHOST','MIRROR')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','shortlisted','parked','selected','rejected')),
  score_summary REAL,
  evidence_state TEXT CHECK (evidence_state IN ('untested','supported','stressed','disputed')),
  next_action TEXT,
  origin_operator_run_id INTEGER NOT NULL REFERENCES operator_runs(operator_run_id),
  frame_id_at_birth INTEGER NOT NULL REFERENCES frames(frame_id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lineage (
  child_idea_id INTEGER NOT NULL REFERENCES ideas(idea_id),
  parent_idea_id INTEGER NOT NULL REFERENCES ideas(idea_id),
  relation TEXT NOT NULL CHECK (relation IN ('derived_from','hybrid_of','refinement_of','counter_of')),
  operator_run_id INTEGER NOT NULL REFERENCES operator_runs(operator_run_id),
  PRIMARY KEY (child_idea_id, parent_idea_id)
);

CREATE TABLE IF NOT EXISTS assessments (
  assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
  idea_id INTEGER NOT NULL REFERENCES ideas(idea_id),
  metric TEXT NOT NULL,
  value TEXT NOT NULL,
  value_numeric REAL,
  rationale TEXT,
  evidence_fact_ids TEXT,
  operator_run_id INTEGER NOT NULL REFERENCES operator_runs(operator_run_id),
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
CREATE INDEX IF NOT EXISTS idx_ideas_kind ON ideas(kind);
CREATE INDEX IF NOT EXISTS idx_ideas_origin_run ON ideas(origin_operator_run_id);
CREATE INDEX IF NOT EXISTS idx_ideas_frame ON ideas(frame_id_at_birth);
CREATE INDEX IF NOT EXISTS idx_assessments_idea ON assessments(idea_id);
CREATE INDEX IF NOT EXISTS idx_assessments_idea_metric_created ON assessments(idea_id, metric, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lineage_child ON lineage(child_idea_id);
CREATE INDEX IF NOT EXISTS idx_lineage_parent ON lineage(parent_idea_id);
CREATE INDEX IF NOT EXISTS idx_op_runs_run_id ON operator_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_op_runs_operator ON operator_runs(operator_name);
CREATE INDEX IF NOT EXISTS idx_frames_active ON frames(active);
CREATE INDEX IF NOT EXISTS idx_facts_stance ON facts(stance);
CREATE INDEX IF NOT EXISTS idx_facts_confidence ON facts(confidence);
"""


# ----------------------------------------------------------------------------
# Connection
# ----------------------------------------------------------------------------


@contextlib.contextmanager
def _connect(slug: str, *, require_exists: bool = True) -> Iterable[sqlite3.Connection]:
    path = _logbook_path(slug)
    if require_exists and not path.exists():
        sys.exit(f"ERROR: no logbook at {path}. Run `init-topic {slug}` first.")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def _rows_to_list(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [_row_to_dict(r) for r in rows]


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def _json_load_safe(text: str | None, default: Any) -> Any:
    if text is None or text == "":
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


# ----------------------------------------------------------------------------
# Topic management
# ----------------------------------------------------------------------------


def cmd_init_topic(args: argparse.Namespace) -> None:
    path = _logbook_path(args.slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _connect(args.slug, require_exists=False) as conn:
        conn.executescript(DDL)
        existing = conn.execute(
            "SELECT topic_slug FROM topic_meta WHERE topic_slug = ?", (args.slug,)
        ).fetchone()
        if existing is None:
            conn.execute(
                "INSERT INTO topic_meta (topic_slug, description, owner, created_at) VALUES (?, ?, ?, ?)",
                (args.slug, args.description or None, args.owner or "personal", _now()),
            )
    print(str(path))


def cmd_list_topics(args: argparse.Namespace) -> None:
    root = _ideation_root()
    if not root.exists():
        _print_json([])
        return
    topics = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("_"):
            continue
        logbook = child / "logbook.sqlite"
        if not logbook.exists():
            continue
        try:
            conn = sqlite3.connect(str(logbook))
            conn.row_factory = sqlite3.Row
            meta = conn.execute(
                "SELECT topic_slug, description, owner, created_at FROM topic_meta LIMIT 1"
            ).fetchone()
            idea_count = conn.execute("SELECT COUNT(*) AS n FROM ideas").fetchone()["n"]
            conn.close()
            if meta is not None:
                topics.append(
                    {
                        **_row_to_dict(meta),
                        "idea_count": idea_count,
                        "path": str(logbook),
                    }
                )
        except sqlite3.Error:
            continue
    _print_json(topics)


def cmd_describe(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        counts = {}
        for tbl in [
            "topic_meta",
            "frames",
            "facts",
            "ideas",
            "lineage",
            "assessments",
            "operator_runs",
        ]:
            counts[tbl] = conn.execute(f"SELECT COUNT(*) AS n FROM {tbl}").fetchone()["n"]
        schema_rows = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        _print_json(
            {
                "path": str(_logbook_path(args.slug)),
                "row_counts": counts,
                "tables": [_row_to_dict(r) for r in schema_rows],
            }
        )


def cmd_show_state(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        meta = conn.execute("SELECT * FROM topic_meta LIMIT 1").fetchone()
        active_frame = conn.execute(
            "SELECT frame_id, version, problem_statement, root_causes, hmw_questions, "
            "triz_contradiction, ifr_statement, created_at FROM frames WHERE active = 1"
        ).fetchone()
        idea_counts = conn.execute(
            "SELECT kind, status, COUNT(*) AS n FROM ideas GROUP BY kind, status"
        ).fetchall()
        assessment_summary = conn.execute(
            "SELECT metric, COUNT(*) AS n FROM assessments GROUP BY metric ORDER BY n DESC"
        ).fetchall()
        recent_ops = conn.execute(
            "SELECT operator_run_id, operator_name, operator_persona, status, "
            "outcome_summary, started_at FROM operator_runs "
            "ORDER BY started_at DESC LIMIT 10"
        ).fetchall()
        state = {
            "topic": _row_to_dict(meta) if meta else None,
            "active_frame": None
            if active_frame is None
            else {
                **_row_to_dict(active_frame),
                "root_causes": _json_load_safe(active_frame["root_causes"], []),
                "hmw_questions": _json_load_safe(active_frame["hmw_questions"], []),
                "triz_contradiction": _json_load_safe(active_frame["triz_contradiction"], None),
            },
            "idea_counts": _rows_to_list(idea_counts),
            "assessment_metrics": _rows_to_list(assessment_summary),
            "recent_operator_runs": _rows_to_list(recent_ops),
        }
        _print_json(state)


# ----------------------------------------------------------------------------
# Operator runs (action log)
# ----------------------------------------------------------------------------


def cmd_op_start(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        cohort = _json_load_safe(args.cohort_ids_json, None)
        if cohort is None:
            sys.exit("ERROR: --cohort-ids-json must parse as a JSON array of integers")
        cur = conn.execute(
            """
            INSERT INTO operator_runs
              (run_id, plan_step_index, operator_name, operator_persona, params,
               cohort_ids, status, user_approved, started_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                args.run_id,
                args.plan_step,
                args.operator,
                args.persona,
                args.params_json,
                json.dumps(cohort),
                1 if args.user_approved else 0,
                _now(),
            ),
        )
        print(cur.lastrowid)


def cmd_op_finalize(args: argparse.Namespace) -> None:
    if args.status == "failed" and not args.error:
        sys.exit("ERROR: --error is required when --status=failed")
    if args.status == "succeeded" and not args.outcome_summary:
        sys.exit("ERROR: --outcome-summary is required when --status=succeeded")
    with _connect(args.slug) as conn:
        conn.execute(
            "UPDATE operator_runs SET status = ?, outcome_summary = ?, error = ?, ended_at = ? "
            "WHERE operator_run_id = ?",
            (args.status, args.outcome_summary, args.error, _now(), args.op_run_id),
        )
    print("ok")


def cmd_op_runs(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        sql = "SELECT * FROM operator_runs WHERE 1=1"
        params: list[Any] = []
        if args.run_id:
            sql += " AND run_id = ?"
            params.append(args.run_id)
        if args.operator:
            sql += " AND operator_name = ?"
            params.append(args.operator)
        sql += " ORDER BY started_at DESC"
        if args.limit:
            sql += " LIMIT ?"
            params.append(args.limit)
        rows = conn.execute(sql, params).fetchall()
        _print_json(_rows_to_list(rows))


# ----------------------------------------------------------------------------
# Frames
# ----------------------------------------------------------------------------


def cmd_add_frame(args: argparse.Namespace) -> None:
    root_causes = _json_load_safe(args.root_causes_json, None)
    if not isinstance(root_causes, list) or not root_causes:
        sys.exit("ERROR: --root-causes-json must parse as a non-empty JSON array of strings")
    hmw = _json_load_safe(args.hmw_questions_json, None)
    if not isinstance(hmw, list) or not hmw:
        sys.exit("ERROR: --hmw-questions-json must parse as a non-empty JSON array of strings")
    triz = None
    if args.triz_contradiction_json:
        triz_obj = _json_load_safe(args.triz_contradiction_json, None)
        if not isinstance(triz_obj, dict):
            sys.exit("ERROR: --triz-contradiction-json must parse as a JSON object")
        triz = json.dumps(triz_obj)

    with _connect(args.slug) as conn:
        prior = conn.execute(
            "SELECT frame_id, version FROM frames WHERE active = 1"
        ).fetchone()
        next_version = (prior["version"] + 1) if prior else 1
        supersedes = prior["frame_id"] if prior else None
        if prior:
            conn.execute("UPDATE frames SET active = 0 WHERE frame_id = ?", (prior["frame_id"],))
        cur = conn.execute(
            """
            INSERT INTO frames
              (version, active, problem_statement, root_causes, hmw_questions,
               triz_contradiction, ifr_statement, supersedes_frame_id,
               operator_run_id, created_at)
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_version,
                args.problem_statement,
                json.dumps(root_causes),
                json.dumps(hmw),
                triz,
                args.ifr_statement,
                supersedes,
                args.operator_run_id,
                _now(),
            ),
        )
        print(cur.lastrowid)


def cmd_active_frame(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        row = conn.execute("SELECT * FROM frames WHERE active = 1").fetchone()
        if row is None:
            _print_json(None)
            return
        data = _row_to_dict(row)
        data["root_causes"] = _json_load_safe(data["root_causes"], [])
        data["hmw_questions"] = _json_load_safe(data["hmw_questions"], [])
        data["triz_contradiction"] = _json_load_safe(data["triz_contradiction"], None)
        _print_json(data)


# ----------------------------------------------------------------------------
# Facts
# ----------------------------------------------------------------------------


_FACT_CONFIDENCES = ("strong", "medium", "weak")
_FACT_STANCES = ("supports", "adversarial", "neutral")


def _insert_fact(
    conn: sqlite3.Connection,
    *,
    claim: str,
    source_url: str | None,
    source_label: str | None,
    confidence: str,
    stance: str,
    operator_run_id: int,
    now: str,
) -> int:
    if confidence not in _FACT_CONFIDENCES:
        sys.exit(f"ERROR: confidence must be one of {_FACT_CONFIDENCES}")
    if stance not in _FACT_STANCES:
        sys.exit(f"ERROR: stance must be one of {_FACT_STANCES}")
    cur = conn.execute(
        """
        INSERT INTO facts
          (claim, source_url, source_label, confidence, stance, operator_run_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (claim, source_url, source_label, confidence, stance, operator_run_id, now),
    )
    return cur.lastrowid


def cmd_add_fact(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        new_id = _insert_fact(
            conn,
            claim=args.claim,
            source_url=args.source_url,
            source_label=args.source_label,
            confidence=args.confidence,
            stance=args.stance,
            operator_run_id=args.operator_run_id,
            now=_now(),
        )
    print(new_id)


def cmd_add_facts_batch(args: argparse.Namespace) -> None:
    """Bulk-insert facts from a JSON file (array of objects).

    Each object supports: claim, confidence, stance, source_url?, source_label?,
    operator_run_id?. Top-level --operator-run-id is the default when absent.
    """
    try:
        payload = json.loads(Path(args.json_file).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"ERROR: could not read batch JSON: {exc}")
    if not isinstance(payload, list):
        sys.exit("ERROR: batch JSON must be a top-level array of fact objects")
    default_op = args.operator_run_id
    ids: list[int] = []
    with _connect(args.slug) as conn:
        now = _now()
        for entry in payload:
            op_id = entry.get("operator_run_id", default_op)
            if op_id is None:
                sys.exit("ERROR: every entry must carry operator_run_id, or pass --operator-run-id")
            new_id = _insert_fact(
                conn,
                claim=entry["claim"],
                source_url=entry.get("source_url"),
                source_label=entry.get("source_label"),
                confidence=entry["confidence"],
                stance=entry["stance"],
                operator_run_id=op_id,
                now=now,
            )
            ids.append(new_id)
    _print_json(ids)


def cmd_facts(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        sql = "SELECT * FROM facts WHERE 1=1"
        params: list[Any] = []
        if args.stance:
            sql += " AND stance = ?"
            params.append(args.stance)
        if args.confidence:
            sql += " AND confidence = ?"
            params.append(args.confidence)
        if args.since:
            sql += " AND created_at >= ?"
            params.append(args.since)
        sql += " ORDER BY created_at DESC"
        if args.limit:
            sql += " LIMIT ?"
            params.append(args.limit)
        rows = conn.execute(sql, params).fetchall()
        _print_json(_rows_to_list(rows))


# ----------------------------------------------------------------------------
# Ideas
# ----------------------------------------------------------------------------

_IDEA_VALID_KINDS = ("seed", "variant", "hybrid", "refinement", "counter")
_IDEA_VALID_TAGS = ("SAFE", "BOLD", "WILD")
_IDEA_VALID_ZONES = ("FIRE", "PLASMA", "ICE", "GHOST", "MIRROR")
_IDEA_VALID_STATUS = ("active", "shortlisted", "parked", "selected", "rejected")
_IDEA_VALID_EVIDENCE = ("untested", "supported", "stressed", "disputed")

_IDEA_MUTABLE = {"status", "score_summary", "evidence_state", "next_action"}


def _insert_idea(
    conn: sqlite3.Connection,
    *,
    title: str,
    description: str,
    kind: str,
    tag: str | None,
    temperature_zone: str | None,
    origin_operator_run_id: int,
    frame_id_at_birth: int | None,
) -> int:
    if kind not in _IDEA_VALID_KINDS:
        sys.exit(f"ERROR: kind must be one of {_IDEA_VALID_KINDS}")
    if tag and tag not in _IDEA_VALID_TAGS:
        sys.exit(f"ERROR: tag must be one of {_IDEA_VALID_TAGS}")
    if temperature_zone and temperature_zone not in _IDEA_VALID_ZONES:
        sys.exit(f"ERROR: temperature_zone must be one of {_IDEA_VALID_ZONES}")
    if frame_id_at_birth is None:
        row = conn.execute(
            "SELECT frame_id FROM frames WHERE active = 1"
        ).fetchone()
        if row is None:
            sys.exit(
                "ERROR: no active frame — run `frame.discover` before generating ideas, "
                "or pass --frame-id-at-birth explicitly."
            )
        frame_id_at_birth = row["frame_id"]
    now = _now()
    cur = conn.execute(
        """
        INSERT INTO ideas
          (title, description, kind, tag, temperature_zone, status, score_summary,
           evidence_state, next_action, origin_operator_run_id, frame_id_at_birth,
           created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'active', NULL, 'untested', NULL, ?, ?, ?, ?)
        """,
        (
            title,
            description,
            kind,
            tag,
            temperature_zone,
            origin_operator_run_id,
            frame_id_at_birth,
            now,
            now,
        ),
    )
    return cur.lastrowid


def cmd_add_idea(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        idea_id = _insert_idea(
            conn,
            title=args.title,
            description=args.description,
            kind=args.kind,
            tag=args.tag,
            temperature_zone=args.zone,
            origin_operator_run_id=args.origin_operator_run_id,
            frame_id_at_birth=args.frame_id_at_birth,
        )
    print(idea_id)


def cmd_add_ideas_batch(args: argparse.Namespace) -> None:
    try:
        payload = json.loads(Path(args.json_file).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"ERROR: could not read batch JSON: {exc}")
    if not isinstance(payload, list):
        sys.exit("ERROR: batch JSON must be a top-level array of idea objects")
    ids: list[int] = []
    with _connect(args.slug) as conn:
        for entry in payload:
            idea_id = _insert_idea(
                conn,
                title=entry["title"],
                description=entry["description"],
                kind=entry["kind"],
                tag=entry.get("tag"),
                temperature_zone=entry.get("temperature_zone"),
                origin_operator_run_id=entry.get(
                    "origin_operator_run_id", args.origin_operator_run_id
                ),
                frame_id_at_birth=entry.get("frame_id_at_birth"),
            )
            ids.append(idea_id)
            # Lineage, if provided inline.
            for parent_id in entry.get("parents", []) or []:
                relation = entry.get("relation", "derived_from")
                _add_lineage_row(
                    conn,
                    child_idea_id=idea_id,
                    parent_idea_id=parent_id,
                    relation=relation,
                    operator_run_id=entry.get(
                        "origin_operator_run_id", args.origin_operator_run_id
                    ),
                )
    _print_json(ids)


def _validate_idea_patch(column: str, value: Any) -> Any:
    if column not in _IDEA_MUTABLE:
        sys.exit(
            f"ERROR: column '{column}' is not mutable. Mutable fields are: "
            f"{sorted(_IDEA_MUTABLE)}"
        )
    if column == "status" and value not in _IDEA_VALID_STATUS:
        sys.exit(f"ERROR: status must be one of {_IDEA_VALID_STATUS}")
    if column == "evidence_state" and value not in _IDEA_VALID_EVIDENCE:
        sys.exit(f"ERROR: evidence_state must be one of {_IDEA_VALID_EVIDENCE}")
    if column == "score_summary":
        try:
            return float(value)
        except (TypeError, ValueError):
            sys.exit("ERROR: score_summary must be a number")
    return value


def cmd_patch_idea(args: argparse.Namespace) -> None:
    value = _validate_idea_patch(args.column, args.value)
    with _connect(args.slug) as conn:
        conn.execute(
            f"UPDATE ideas SET {args.column} = ?, updated_at = ? WHERE idea_id = ?",
            (value, _now(), args.idea_id),
        )
    print("ok")


def cmd_patch_ideas_batch(args: argparse.Namespace) -> None:
    """Bulk-patch mutable fields on ideas from a JSON file.

    The file is a JSON array of patch objects: `{idea_id, column, value}`.
    A single entry applies one column update to one idea. Multiple columns on
    the same idea appear as multiple entries. All updates run in one
    transaction — N patches for the cost of ~1 subprocess + ~1 commit.
    """
    try:
        payload = json.loads(Path(args.json_file).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"ERROR: could not read batch JSON: {exc}")
    if not isinstance(payload, list):
        sys.exit("ERROR: batch JSON must be a top-level array of patch objects")
    now = _now()
    with _connect(args.slug) as conn:
        for entry in payload:
            value = _validate_idea_patch(entry["column"], entry["value"])
            conn.execute(
                f"UPDATE ideas SET {entry['column']} = ?, updated_at = ? WHERE idea_id = ?",
                (value, now, entry["idea_id"]),
            )
    print("ok")


def cmd_add_lineage_batch(args: argparse.Namespace) -> None:
    """Bulk-insert lineage edges from a JSON file.

    Each entry: `{child_idea_id, parent_idea_id, relation, operator_run_id?}`.
    Top-level --operator-run-id is the default when an entry omits it.
    """
    try:
        payload = json.loads(Path(args.json_file).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"ERROR: could not read batch JSON: {exc}")
    if not isinstance(payload, list):
        sys.exit("ERROR: batch JSON must be a top-level array of lineage objects")
    default_op = args.operator_run_id
    with _connect(args.slug) as conn:
        for entry in payload:
            op_id = entry.get("operator_run_id", default_op)
            if op_id is None:
                sys.exit("ERROR: every entry must carry operator_run_id, or pass --operator-run-id")
            _add_lineage_row(
                conn,
                child_idea_id=entry["child_idea_id"],
                parent_idea_id=entry["parent_idea_id"],
                relation=entry["relation"],
                operator_run_id=op_id,
            )
    print("ok")


def cmd_ideas(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        sql = "SELECT * FROM ideas WHERE 1=1"
        params: list[Any] = []
        if args.status:
            sql += " AND status = ?"
            params.append(args.status)
        if args.kind:
            sql += " AND kind = ?"
            params.append(args.kind)
        if args.tag:
            sql += " AND tag = ?"
            params.append(args.tag)
        if args.zone:
            sql += " AND temperature_zone = ?"
            params.append(args.zone)
        if args.frame_id:
            sql += " AND frame_id_at_birth = ?"
            params.append(args.frame_id)
        sql += " ORDER BY idea_id"
        if args.limit:
            sql += " LIMIT ?"
            params.append(args.limit)
        rows = conn.execute(sql, params).fetchall()
        _print_json(_rows_to_list(rows))


def cmd_idea(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        idea_row = conn.execute(
            "SELECT * FROM ideas WHERE idea_id = ?", (args.idea_id,)
        ).fetchone()
        if idea_row is None:
            sys.exit(f"ERROR: idea #{args.idea_id} not found")
        # Latest assessment per metric.
        latest = conn.execute(
            """
            SELECT metric, value, value_numeric, rationale, evidence_fact_ids, created_at
            FROM assessments a1
            WHERE idea_id = ?
              AND created_at = (
                SELECT MAX(created_at) FROM assessments a2
                WHERE a2.idea_id = a1.idea_id AND a2.metric = a1.metric
              )
            ORDER BY metric
            """,
            (args.idea_id,),
        ).fetchall()
        parents = conn.execute(
            """
            SELECT p.idea_id, p.title, p.kind, l.relation
            FROM lineage l
            JOIN ideas p ON p.idea_id = l.parent_idea_id
            WHERE l.child_idea_id = ?
            """,
            (args.idea_id,),
        ).fetchall()
        children = conn.execute(
            """
            SELECT c.idea_id, c.title, c.kind, l.relation
            FROM lineage l
            JOIN ideas c ON c.idea_id = l.child_idea_id
            WHERE l.parent_idea_id = ?
            """,
            (args.idea_id,),
        ).fetchall()
        _print_json(
            {
                "idea": _row_to_dict(idea_row),
                "latest_assessments_by_metric": [
                    {
                        **_row_to_dict(r),
                        "evidence_fact_ids": _json_load_safe(r["evidence_fact_ids"], None),
                    }
                    for r in latest
                ],
                "parents": _rows_to_list(parents),
                "children": _rows_to_list(children),
            }
        )


# ----------------------------------------------------------------------------
# Lineage
# ----------------------------------------------------------------------------

_LINEAGE_RELATIONS = ("derived_from", "hybrid_of", "refinement_of", "counter_of")


def _add_lineage_row(
    conn: sqlite3.Connection,
    *,
    child_idea_id: int,
    parent_idea_id: int,
    relation: str,
    operator_run_id: int,
) -> None:
    if relation not in _LINEAGE_RELATIONS:
        sys.exit(f"ERROR: relation must be one of {_LINEAGE_RELATIONS}")
    if child_idea_id == parent_idea_id:
        sys.exit("ERROR: self-loops in lineage are not allowed")
    conn.execute(
        """
        INSERT OR IGNORE INTO lineage
          (child_idea_id, parent_idea_id, relation, operator_run_id)
        VALUES (?, ?, ?, ?)
        """,
        (child_idea_id, parent_idea_id, relation, operator_run_id),
    )


def cmd_add_lineage(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        _add_lineage_row(
            conn,
            child_idea_id=args.child,
            parent_idea_id=args.parent,
            relation=args.relation,
            operator_run_id=args.operator_run_id,
        )
    print("ok")


def cmd_children_of(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        rows = conn.execute(
            """
            SELECT i.idea_id, i.title, i.kind, l.relation
            FROM lineage l
            JOIN ideas i ON i.idea_id = l.child_idea_id
            WHERE l.parent_idea_id = ?
            """,
            (args.idea_id,),
        ).fetchall()
        _print_json(_rows_to_list(rows))


def cmd_ancestors_of(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        rows = conn.execute(
            """
            SELECT i.idea_id, i.title, i.kind, l.relation
            FROM lineage l
            JOIN ideas i ON i.idea_id = l.parent_idea_id
            WHERE l.child_idea_id = ?
            """,
            (args.idea_id,),
        ).fetchall()
        _print_json(_rows_to_list(rows))


def cmd_lineage_tree(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        rows = conn.execute(
            """
            WITH RECURSIVE ancestry(idea_id, depth) AS (
              SELECT ?, 0
              UNION ALL
              SELECT l.parent_idea_id, a.depth + 1
              FROM lineage l
              JOIN ancestry a ON l.child_idea_id = a.idea_id
            )
            SELECT i.idea_id, i.kind, i.title, a.depth
            FROM ancestry a
            JOIN ideas i ON i.idea_id = a.idea_id
            ORDER BY a.depth, i.idea_id
            """,
            (args.idea_id,),
        ).fetchall()
        _print_json(_rows_to_list(rows))


# ----------------------------------------------------------------------------
# Assessments
# ----------------------------------------------------------------------------

_METRIC_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


def _insert_assessment(
    conn: sqlite3.Connection,
    *,
    idea_id: int,
    metric: str,
    value: str,
    value_numeric: float | None,
    rationale: str | None,
    evidence_fact_ids: list[int] | None,
    operator_run_id: int,
    now: str,
) -> int:
    if not _METRIC_PATTERN.match(metric):
        sys.exit(
            f"ERROR: metric '{metric}' must match ^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$"
        )
    evidence_json = (
        json.dumps(evidence_fact_ids) if evidence_fact_ids is not None else None
    )
    cur = conn.execute(
        """
        INSERT INTO assessments
          (idea_id, metric, value, value_numeric, rationale,
           evidence_fact_ids, operator_run_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            idea_id,
            metric,
            value,
            value_numeric,
            rationale,
            evidence_json,
            operator_run_id,
            now,
        ),
    )
    return cur.lastrowid


def cmd_add_assessment(args: argparse.Namespace) -> None:
    evidence = None
    if args.evidence_fact_ids_json:
        obj = _json_load_safe(args.evidence_fact_ids_json, None)
        if not isinstance(obj, list):
            sys.exit("ERROR: --evidence-fact-ids-json must be a JSON array")
        evidence = obj
    with _connect(args.slug) as conn:
        cur_id = _insert_assessment(
            conn,
            idea_id=args.idea_id,
            metric=args.metric,
            value=args.value,
            value_numeric=args.value_numeric,
            rationale=args.rationale,
            evidence_fact_ids=evidence,
            operator_run_id=args.operator_run_id,
            now=_now(),
        )
    print(cur_id)


def cmd_add_assessments_batch(args: argparse.Namespace) -> None:
    """Bulk-insert assessments from a JSON file (array of objects).

    Each object supports: idea_id, metric, value, value_numeric?, rationale?,
    evidence_fact_ids?, operator_run_id?. Top-level --operator-run-id is the
    default when an entry omits it. All inserts happen in a single transaction,
    giving N assessments for the cost of ~1 subprocess + ~1 commit.
    """
    try:
        payload = json.loads(Path(args.json_file).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"ERROR: could not read batch JSON: {exc}")
    if not isinstance(payload, list):
        sys.exit("ERROR: batch JSON must be a top-level array of assessment objects")
    default_op = args.operator_run_id
    ids: list[int] = []
    with _connect(args.slug) as conn:
        now = _now()
        for entry in payload:
            op_id = entry.get("operator_run_id", default_op)
            if op_id is None:
                sys.exit("ERROR: every entry must carry operator_run_id, or pass --operator-run-id")
            evidence_fact_ids = entry.get("evidence_fact_ids")
            if evidence_fact_ids is not None and not isinstance(evidence_fact_ids, list):
                sys.exit("ERROR: evidence_fact_ids must be a JSON array when present")
            new_id = _insert_assessment(
                conn,
                idea_id=entry["idea_id"],
                metric=entry["metric"],
                value=str(entry["value"]),
                value_numeric=entry.get("value_numeric"),
                rationale=entry.get("rationale"),
                evidence_fact_ids=evidence_fact_ids,
                operator_run_id=op_id,
                now=now,
            )
            ids.append(new_id)
    _print_json(ids)


def cmd_latest_assessment(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        row = conn.execute(
            """
            SELECT * FROM assessments
            WHERE idea_id = ? AND metric = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (args.idea_id, args.metric),
        ).fetchone()
        if row is None:
            _print_json(None)
            return
        data = _row_to_dict(row)
        data["evidence_fact_ids"] = _json_load_safe(data["evidence_fact_ids"], None)
        _print_json(data)


def cmd_assessments(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        sql = "SELECT * FROM assessments WHERE 1=1"
        params: list[Any] = []
        if args.idea_id:
            sql += " AND idea_id = ?"
            params.append(args.idea_id)
        if args.metric:
            sql += " AND metric = ?"
            params.append(args.metric)
        sql += " ORDER BY idea_id, metric, created_at DESC"
        if args.limit:
            sql += " LIMIT ?"
            params.append(args.limit)
        rows = conn.execute(sql, params).fetchall()
        _print_json(_rows_to_list(rows))


# ----------------------------------------------------------------------------
# Cohort queries — return JSON arrays of idea_ids
# ----------------------------------------------------------------------------


def _query_top_by_composite(conn: sqlite3.Connection, n: int, status: str | None) -> list[int]:
    sql = (
        "SELECT idea_id FROM ideas "
        "WHERE score_summary IS NOT NULL"
    )
    params: list[Any] = []
    if status:
        sql += " AND status = ?"
        params.append(status)
    else:
        sql += " AND status IN ('active','shortlisted')"
    sql += " ORDER BY score_summary DESC LIMIT ?"
    params.append(n)
    return [r["idea_id"] for r in conn.execute(sql, params).fetchall()]


def _query_top_by_metric(conn: sqlite3.Connection, metric: str, n: int) -> list[int]:
    sql = """
    WITH latest AS (
      SELECT idea_id, value_numeric,
             ROW_NUMBER() OVER (PARTITION BY idea_id ORDER BY created_at DESC) AS rn
      FROM assessments
      WHERE metric = ? AND value_numeric IS NOT NULL
    )
    SELECT i.idea_id
    FROM ideas i
    JOIN latest ON latest.idea_id = i.idea_id AND latest.rn = 1
    WHERE i.status IN ('active','shortlisted')
    ORDER BY latest.value_numeric DESC
    LIMIT ?
    """
    return [r["idea_id"] for r in conn.execute(sql, (metric, n)).fetchall()]


def _query_children_of(conn: sqlite3.Connection, idea_id: int) -> list[int]:
    return [
        r["idea_id"]
        for r in conn.execute(
            "SELECT child_idea_id AS idea_id FROM lineage WHERE parent_idea_id = ?",
            (idea_id,),
        ).fetchall()
    ]


def _query_tension_cluster(conn: sqlite3.Connection) -> list[int]:
    sql = """
    WITH latest_tension_run AS (
      SELECT operator_run_id FROM operator_runs
      WHERE operator_name = 'evaluate.tension' AND status = 'succeeded'
      ORDER BY started_at DESC LIMIT 1
    )
    SELECT DISTINCT a.idea_id
    FROM assessments a
    JOIN latest_tension_run ON a.operator_run_id = latest_tension_run.operator_run_id
    WHERE a.metric LIKE 'tension.%'
    ORDER BY a.idea_id
    """
    return [r["idea_id"] for r in conn.execute(sql).fetchall()]


def _query_all_seeds(conn: sqlite3.Connection) -> list[int]:
    return [
        r["idea_id"]
        for r in conn.execute(
            "SELECT idea_id FROM ideas WHERE kind = 'seed' AND status = 'active' ORDER BY idea_id"
        ).fetchall()
    ]


def _query_all_active(conn: sqlite3.Connection) -> list[int]:
    return [
        r["idea_id"]
        for r in conn.execute(
            "SELECT idea_id FROM ideas WHERE status = 'active' ORDER BY idea_id"
        ).fetchall()
    ]


def _query_diversity_top(conn: sqlite3.Connection, n: int) -> list[int]:
    """
    Spread across (tag, temperature_zone) buckets weighted by recency.
    Algorithm: bucket active ideas by (tag, zone); within each bucket pick the
    most recent; round-robin through buckets until we hit n.
    """
    rows = conn.execute(
        "SELECT idea_id, tag, temperature_zone, created_at FROM ideas "
        "WHERE status IN ('active','shortlisted') ORDER BY created_at DESC"
    ).fetchall()
    buckets: dict[tuple[Any, Any], list[int]] = {}
    for r in rows:
        key = (r["tag"], r["temperature_zone"])
        buckets.setdefault(key, []).append(r["idea_id"])
    picked: list[int] = []
    while len(picked) < n and any(buckets.values()):
        for key in list(buckets.keys()):
            if not buckets[key]:
                continue
            picked.append(buckets[key].pop(0))
            if len(picked) >= n:
                break
    return picked


def cmd_query(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        if args.query == "top-by-composite":
            n = args.n or 5
            ids = _query_top_by_composite(conn, n, args.status)
        elif args.query == "top-by-metric":
            if not args.metric:
                sys.exit("ERROR: --metric required for top-by-metric")
            n = args.n or 5
            ids = _query_top_by_metric(conn, args.metric, n)
        elif args.query == "children-of":
            if not args.id:
                sys.exit("ERROR: --id required for children-of")
            ids = _query_children_of(conn, args.id)
        elif args.query == "tension-cluster":
            ids = _query_tension_cluster(conn)
        elif args.query == "all-seeds":
            ids = _query_all_seeds(conn)
        elif args.query == "all-active":
            ids = _query_all_active(conn)
        elif args.query == "diversity-top":
            n = args.n or 5
            ids = _query_diversity_top(conn, n)
        else:
            sys.exit(f"ERROR: unknown query '{args.query}'")
    _print_json(ids)


# ----------------------------------------------------------------------------
# Export
# ----------------------------------------------------------------------------


def cmd_export_md(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        sql = "SELECT * FROM ideas WHERE 1=1"
        params: list[Any] = []
        if args.status:
            sql += " AND status = ?"
            params.append(args.status)
        if args.kind:
            sql += " AND kind = ?"
            params.append(args.kind)
        sql += " ORDER BY idea_id"
        rows = conn.execute(sql, params).fetchall()
    print(f"# Ideas — {args.slug}\n")
    for r in rows:
        print(f"## Idea #{r['idea_id']} — {r['title']}  ")
        print(
            f"*{r['kind']}* · tag={r['tag'] or '—'} · zone={r['temperature_zone'] or '—'} · "
            f"status={r['status']} · evidence={r['evidence_state'] or '—'}"
        )
        print()
        print(r["description"])
        print()


def cmd_export_menu(args: argparse.Namespace) -> None:
    with _connect(args.slug) as conn:
        # Pull latest menu_bucket assessment per shortlisted/selected idea.
        rows = conn.execute(
            """
            WITH latest_bucket AS (
              SELECT idea_id, value AS bucket,
                     ROW_NUMBER() OVER (PARTITION BY idea_id ORDER BY created_at DESC) AS rn
              FROM assessments
              WHERE metric = 'menu_bucket'
            )
            SELECT i.idea_id, i.title, i.description, i.tag, lb.bucket
            FROM ideas i
            LEFT JOIN latest_bucket lb ON lb.idea_id = i.idea_id AND lb.rn = 1
            WHERE i.status IN ('shortlisted','selected')
            ORDER BY
              CASE lb.bucket
                WHEN 'quick_win' THEN 1
                WHEN 'core_bet' THEN 2
                WHEN 'moonshot' THEN 3
                ELSE 4
              END,
              i.idea_id
            """
        ).fetchall()
    buckets: dict[str, list[dict[str, Any]]] = {
        "Quick Wins": [],
        "Core Bets": [],
        "Moonshots": [],
        "Unbucketed": [],
    }
    label_of = {
        "quick_win": "Quick Wins",
        "core_bet": "Core Bets",
        "moonshot": "Moonshots",
    }
    for r in rows:
        label = label_of.get(r["bucket"], "Unbucketed")
        buckets[label].append(_row_to_dict(r))
    print(f"# Idea Menu — {args.slug}\n")
    for label, entries in buckets.items():
        if not entries:
            continue
        print(f"## {label}\n")
        for e in entries:
            print(f"### Idea #{e['idea_id']} — {e['title']}  ")
            print(f"*tag={e['tag'] or '—'}*\n")
            print(e["description"])
            print()


# ----------------------------------------------------------------------------
# Utility: generate a run_id
# ----------------------------------------------------------------------------


def cmd_new_run_id(args: argparse.Namespace) -> None:
    print(str(uuid.uuid4()))


# ----------------------------------------------------------------------------
# Operator catalog
# ----------------------------------------------------------------------------


def _resolve_operators_dir() -> "Path":
    env = os.environ.get("IDEATION_OPERATORS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "operators"


def cmd_list_operators(args: argparse.Namespace) -> None:
    import operator_meta

    ops_dir = _resolve_operators_dir()
    try:
        catalog = operator_meta.load_catalog(ops_dir)
    except (operator_meta.FrontmatterError, operator_meta.LintError) as e:
        sys.exit(f"ERROR: {e}")

    payload = {"operators": catalog}
    if args.format == "json":
        _print_json(payload)
    else:
        # Deterministic YAML-ish rendering — mirrors the input grammar.
        print(_render_catalog_yaml(payload))


def cmd_lint_operators(args: argparse.Namespace) -> None:
    import operator_meta

    ops_dir = _resolve_operators_dir()
    errors_total = 0
    per_file: list[tuple[str, list[str]]] = []

    raw: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(ops_dir.glob("*.md")):
        try:
            text = path.read_text()
            meta = operator_meta.parse_frontmatter(text)
        except operator_meta.FrontmatterError as e:
            per_file.append((path.name, [f"frontmatter parse: {e}"]))
            errors_total += 1
            continue
        except (OSError, UnicodeDecodeError) as e:
            per_file.append((path.name, [f"read error: {e}"]))
            errors_total += 1
            continue
        raw.append((path.name, meta))

    known_names = {m["name"] for _, m in raw if "name" in m}
    for filename, meta in raw:
        errs = operator_meta.lint_operator(meta, filename, known_operator_names=known_names)
        if errs:
            per_file.append((filename, errs))
            errors_total += len(errs)

    if per_file:
        for filename, errs in per_file:
            print(f"{filename}:")
            for e in errs:
                print(f"  - {e}")
        err_word = "error" if errors_total == 1 else "errors"
        file_word = "file" if len(per_file) == 1 else "files"
        print(f"\n{errors_total} {err_word} across {len(per_file)} operator {file_word}.")
        sys.exit(1)

    file_word = "file" if len(raw) == 1 else "files"
    print(f"0 errors across {len(raw)} operator {file_word}.")


_REFERENCE_BANNER = (
    "<!--\n"
    "This file is generated from operator frontmatter.\n"
    "Regenerate with: `python plugins/ideation/skills/ideation/scripts/ideation_db.py generate-reference`\n"
    "Do not edit by hand — your changes will be overwritten.\n"
    "-->\n"
)

_STAGE_TITLES = {
    "frame": "Frame operators",
    "generate": "Generate operators",
    "transform": "Transform operators",
    "evaluate": "Evaluate operators",
    "validate": "Validate operators",
    "decide": "Decide operators",
}

_STAGE_ORDER = ("frame", "generate", "transform", "evaluate", "validate", "decide")


def _render_reference(catalog: list[dict[str, Any]]) -> str:
    by_stage: dict[str, list[dict[str, Any]]] = {s: [] for s in _STAGE_ORDER}
    for entry in catalog:
        by_stage.setdefault(entry["stage"], []).append(entry)

    out: list[str] = [_REFERENCE_BANNER, "# When to use which operator", ""]
    out.append(
        "Generated from operator frontmatter. Grouped by stage. "
        "For each operator, the **scope** line tells the router how it consumes ideas; "
        "**Use when** and **Avoid when** are the judgment cues."
    )
    out.append("")

    for stage in _STAGE_ORDER:
        entries = sorted(by_stage.get(stage, []), key=lambda e: e["name"])
        if not entries:
            continue
        out.append(f"## {_STAGE_TITLES[stage]}")
        out.append("")
        for e in entries:
            out.append(f"### {e['name']}")
            out.append("")
            out.append(f"- **scope:** {e['scope']}")
            kinds = e["applies_to"]["kinds"]
            kinds_str = ", ".join(kinds) if kinds else "—"
            out.append(f"- **applies to kinds:** {kinds_str}")
            out.append(f"- **min cohort:** {e['applies_to']['min_cohort']}")
            out.append("- **Use when:**")
            for cue in e["use_when"]:
                out.append(f"  - {cue}")
            out.append("- **Avoid when:**")
            for cue in e["avoid_when"]:
                out.append(f"  - {cue}")
            if e["followups"]:
                out.append("- **Typical followups:** " + ", ".join(e["followups"]))
            out.append("")

    return "\n".join(out) + "\n" if not out[-1].endswith("\n") else "\n".join(out)


def cmd_generate_reference(args: argparse.Namespace) -> None:
    import operator_meta

    ops_dir = _resolve_operators_dir()
    try:
        catalog = operator_meta.load_catalog(ops_dir)
    except (operator_meta.FrontmatterError, operator_meta.LintError) as e:
        sys.exit(f"ERROR: {e}")

    rendered = _render_reference(catalog)
    output = Path(args.output) if args.output else (
        Path(__file__).resolve().parent.parent / "references" / "when-to-use-which-operator.md"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered)
    print(str(output))


def _render_catalog_yaml(payload: dict[str, Any]) -> str:
    """Render the catalog as a YAML-ish text block for display only.

    Output uses inline-dict syntax (e.g. produces: {ideas: true, ...}) which
    the operator_meta frontmatter parser does not round-trip. Do not feed
    this output back into parse_frontmatter.
    """
    lines: list[str] = ["operators:"]
    for entry in payload["operators"]:
        lines.append(f"  - name: {entry['name']}")
        lines.append(f"    stage: {entry['stage']}")
        lines.append(f"    scope: {entry['scope']}")
        lines.append("    applies_to:")
        kinds = entry["applies_to"]["kinds"]
        lines.append(f"      kinds: [{', '.join(kinds)}]")
        lines.append(f"      min_cohort: {entry['applies_to']['min_cohort']}")
        lines.append("    use_when:")
        for cue in entry["use_when"]:
            lines.append(f"      - {cue}")
        lines.append("    avoid_when:")
        for cue in entry["avoid_when"]:
            lines.append(f"      - {cue}")
        produces = entry["produces"]
        lines.append(
            "    produces: {"
            f"ideas: {str(produces['ideas']).lower()}, "
            f"assessments: {str(produces['assessments']).lower()}, "
            f"facts: {str(produces['facts']).lower()}"
            "}"
        )
        lines.append("    cost: {web: " + str(entry["cost"]["web"]).lower() + "}")
        lines.append(
            f"    repeat_guard: {{same_lineage_cooldown: {entry['repeat_guard']['same_lineage_cooldown']}}}"
        )
        if entry["followups"]:
            lines.append("    followups:")
            for fn in entry["followups"]:
                lines.append(f"      - {fn}")
        else:
            lines.append("    followups: []")
    return "\n".join(lines) + "\n"


# ----------------------------------------------------------------------------
# argparse
# ----------------------------------------------------------------------------


def _add_slug(p: argparse.ArgumentParser) -> None:
    p.add_argument("slug", help="Topic slug (directory name under .ideation/)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ideation_db.py",
        description="SQLite CLI for the ideation skill.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Topic management
    p = sub.add_parser("init-topic", help="Create a new topic logbook")
    _add_slug(p)
    p.add_argument("--description")
    p.add_argument("--owner", default="personal")
    p.set_defaults(func=cmd_init_topic)

    p = sub.add_parser("list-topics", help="List all topics in the current ideation root")
    p.set_defaults(func=cmd_list_topics)

    p = sub.add_parser("describe", help="Schema + row counts for a topic")
    _add_slug(p)
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("show-state", help="Active frame + idea counts + recent operator runs")
    _add_slug(p)
    p.set_defaults(func=cmd_show_state)

    # Operator runs
    p = sub.add_parser("op-start", help="Insert operator_runs row (status=pending); returns operator_run_id")
    _add_slug(p)
    p.add_argument("--run-id", required=True)
    p.add_argument("--plan-step", type=int)
    p.add_argument("--operator", required=True, help="Fully qualified operator name, e.g. transform.scamper")
    p.add_argument("--persona")
    p.add_argument("--params-json")
    p.add_argument("--cohort-ids-json", required=True, help="JSON array of idea_ids")
    p.add_argument("--user-approved", action="store_true", default=True)
    p.set_defaults(func=cmd_op_start)

    p = sub.add_parser("op-finalize", help="Patch operator_runs row to terminal status")
    _add_slug(p)
    p.add_argument("op_run_id", type=int)
    p.add_argument("--status", required=True, choices=("succeeded", "failed", "skipped"))
    p.add_argument("--outcome-summary")
    p.add_argument("--error")
    p.set_defaults(func=cmd_op_finalize)

    p = sub.add_parser("op-runs", help="List operator runs")
    _add_slug(p)
    p.add_argument("--run-id")
    p.add_argument("--operator")
    p.add_argument("--limit", type=int, default=100)
    p.set_defaults(func=cmd_op_runs)

    # Frames
    p = sub.add_parser("add-frame", help="Insert new active frame (supersedes prior active)")
    _add_slug(p)
    p.add_argument("--problem-statement", required=True)
    p.add_argument("--root-causes-json", required=True)
    p.add_argument("--hmw-questions-json", required=True)
    p.add_argument("--triz-contradiction-json")
    p.add_argument("--ifr-statement")
    p.add_argument("--operator-run-id", type=int, required=True)
    p.set_defaults(func=cmd_add_frame)

    p = sub.add_parser("active-frame", help="Print the currently active frame")
    _add_slug(p)
    p.set_defaults(func=cmd_active_frame)

    # Facts
    p = sub.add_parser("add-fact", help="Append a fact")
    _add_slug(p)
    p.add_argument("--claim", required=True)
    p.add_argument("--confidence", required=True, choices=("strong", "medium", "weak"))
    p.add_argument("--stance", required=True, choices=("supports", "adversarial", "neutral"))
    p.add_argument("--source-url")
    p.add_argument("--source-label")
    p.add_argument("--operator-run-id", type=int, required=True)
    p.set_defaults(func=cmd_add_fact)

    p = sub.add_parser(
        "add-facts-batch",
        help="Bulk insert facts from a JSON file; returns JSON array of fact_ids",
    )
    _add_slug(p)
    p.add_argument("json_file")
    p.add_argument(
        "--operator-run-id",
        type=int,
        help="Default operator_run_id used when a batch entry omits it",
    )
    p.set_defaults(func=cmd_add_facts_batch)

    p = sub.add_parser("facts", help="List facts with optional filters")
    _add_slug(p)
    p.add_argument("--stance", choices=("supports", "adversarial", "neutral"))
    p.add_argument("--confidence", choices=("strong", "medium", "weak"))
    p.add_argument("--since")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_facts)

    # Ideas
    p = sub.add_parser("add-idea", help="Insert a new idea; returns idea_id")
    _add_slug(p)
    p.add_argument("--title", required=True)
    p.add_argument("--description", required=True)
    p.add_argument("--kind", required=True, choices=_IDEA_VALID_KINDS)
    p.add_argument("--tag", choices=_IDEA_VALID_TAGS)
    p.add_argument("--zone", choices=_IDEA_VALID_ZONES, dest="zone")
    p.add_argument("--origin-operator-run-id", type=int, required=True)
    p.add_argument(
        "--frame-id-at-birth",
        type=int,
        help="FK to frames.frame_id; if omitted, resolves to the active frame at insert time",
    )
    p.set_defaults(func=cmd_add_idea)

    p = sub.add_parser(
        "add-ideas-batch",
        help="Bulk insert ideas from a JSON file; returns JSON array of assigned idea_ids",
    )
    _add_slug(p)
    p.add_argument("json_file")
    p.add_argument(
        "--origin-operator-run-id",
        type=int,
        help="Default operator_run_id used when a batch entry omits it",
    )
    p.set_defaults(func=cmd_add_ideas_batch)

    p = sub.add_parser("patch-idea", help="Patch a mutable field on an idea")
    _add_slug(p)
    p.add_argument("idea_id", type=int)
    p.add_argument("column")
    p.add_argument("value")
    p.set_defaults(func=cmd_patch_idea)

    p = sub.add_parser(
        "patch-ideas-batch",
        help="Bulk patch mutable fields on ideas from a JSON file ([{idea_id,column,value}, ...])",
    )
    _add_slug(p)
    p.add_argument("json_file")
    p.set_defaults(func=cmd_patch_ideas_batch)

    p = sub.add_parser("ideas", help="List ideas with filters")
    _add_slug(p)
    p.add_argument("--status", choices=_IDEA_VALID_STATUS)
    p.add_argument("--kind", choices=_IDEA_VALID_KINDS)
    p.add_argument("--tag", choices=_IDEA_VALID_TAGS)
    p.add_argument("--zone", choices=_IDEA_VALID_ZONES, dest="zone")
    p.add_argument("--frame-id", type=int)
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_ideas)

    p = sub.add_parser("idea", help="One idea + assessments + lineage")
    _add_slug(p)
    p.add_argument("idea_id", type=int)
    p.set_defaults(func=cmd_idea)

    # Lineage
    p = sub.add_parser("add-lineage", help="Add a parent→child edge")
    _add_slug(p)
    p.add_argument("--child", type=int, required=True)
    p.add_argument("--parent", type=int, required=True)
    p.add_argument("--relation", required=True, choices=_LINEAGE_RELATIONS)
    p.add_argument("--operator-run-id", type=int, required=True)
    p.set_defaults(func=cmd_add_lineage)

    p = sub.add_parser(
        "add-lineage-batch",
        help="Bulk insert lineage edges from a JSON file ([{child_idea_id,parent_idea_id,relation}, ...])",
    )
    _add_slug(p)
    p.add_argument("json_file")
    p.add_argument(
        "--operator-run-id",
        type=int,
        help="Default operator_run_id used when a batch entry omits it",
    )
    p.set_defaults(func=cmd_add_lineage_batch)

    p = sub.add_parser("children-of", help="Direct children of an idea")
    _add_slug(p)
    p.add_argument("idea_id", type=int)
    p.set_defaults(func=cmd_children_of)

    p = sub.add_parser("ancestors-of", help="Direct parents of an idea")
    _add_slug(p)
    p.add_argument("idea_id", type=int)
    p.set_defaults(func=cmd_ancestors_of)

    p = sub.add_parser("lineage-tree", help="Full ancestry tree of an idea (recursive)")
    _add_slug(p)
    p.add_argument("idea_id", type=int)
    p.set_defaults(func=cmd_lineage_tree)

    # Assessments
    p = sub.add_parser("add-assessment", help="Append an assessment row")
    _add_slug(p)
    p.add_argument("--idea-id", type=int, required=True)
    p.add_argument("--metric", required=True)
    p.add_argument("--value", required=True)
    p.add_argument("--value-numeric", type=float)
    p.add_argument("--rationale")
    p.add_argument("--evidence-fact-ids-json")
    p.add_argument("--operator-run-id", type=int, required=True)
    p.set_defaults(func=cmd_add_assessment)

    p = sub.add_parser(
        "add-assessments-batch",
        help="Bulk insert assessments from a JSON file; returns JSON array of assessment_ids",
    )
    _add_slug(p)
    p.add_argument("json_file")
    p.add_argument(
        "--operator-run-id",
        type=int,
        help="Default operator_run_id used when a batch entry omits it",
    )
    p.set_defaults(func=cmd_add_assessments_batch)

    p = sub.add_parser("latest-assessment", help="Latest assessment for (idea_id, metric)")
    _add_slug(p)
    p.add_argument("--idea-id", type=int, required=True)
    p.add_argument("--metric", required=True)
    p.set_defaults(func=cmd_latest_assessment)

    p = sub.add_parser("assessments", help="List assessments with filters")
    _add_slug(p)
    p.add_argument("--idea-id", type=int)
    p.add_argument("--metric")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_assessments)

    # Cohort queries
    p = sub.add_parser(
        "query",
        help="Named cohort query — returns JSON array of idea_ids",
    )
    _add_slug(p)
    p.add_argument(
        "query",
        choices=(
            "top-by-composite",
            "top-by-metric",
            "children-of",
            "tension-cluster",
            "all-seeds",
            "all-active",
            "diversity-top",
        ),
    )
    p.add_argument("--n", type=int, help="N for top-by-* and diversity-top")
    p.add_argument("--metric")
    p.add_argument("--id", type=int, help="idea id for children-of")
    p.add_argument("--status", choices=_IDEA_VALID_STATUS, help="override for top-by-composite")
    p.set_defaults(func=cmd_query)

    # Export
    p = sub.add_parser("export-md", help="Dump ideas as markdown")
    _add_slug(p)
    p.add_argument("--status", choices=_IDEA_VALID_STATUS)
    p.add_argument("--kind", choices=_IDEA_VALID_KINDS)
    p.set_defaults(func=cmd_export_md)

    p = sub.add_parser("export-menu", help="Render the idea menu (quick wins / core bets / moonshots)")
    _add_slug(p)
    p.set_defaults(func=cmd_export_menu)

    # Operator catalog
    p = sub.add_parser("list-operators", help="Print the operator frontmatter catalog")
    p.add_argument("--format", choices=("yaml", "json"), default="yaml")
    p.set_defaults(func=cmd_list_operators)

    p = sub.add_parser("lint-operators", help="Validate operator frontmatter across the catalog")
    p.set_defaults(func=cmd_lint_operators)

    p = sub.add_parser(
        "generate-reference",
        help="Render the when-to-use-which-operator.md doc from frontmatter",
    )
    p.add_argument("--output", help="Output path (default: references/when-to-use-which-operator.md)")
    p.set_defaults(func=cmd_generate_reference)

    # Utility
    p = sub.add_parser("new-run-id", help="Print a fresh UUID to use as run_id")
    p.set_defaults(func=cmd_new_run_id)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
