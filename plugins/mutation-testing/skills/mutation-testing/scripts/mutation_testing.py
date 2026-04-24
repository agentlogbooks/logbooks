#!/usr/bin/env python3
"""
Mutation testing runner — applies mutations from a JSON file and runs the project test suite.
Call with --mutations-file pointing at pre-generated mutations (JSON array) and
--test-command specifying the test suite command (must be the last flag).
"""

import subprocess
import json
import sys
import sqlite3
import argparse
import platform
import hashlib
import secrets
from datetime import datetime, timezone
from pathlib import Path

# On Windows, .cmd wrappers (npx, jest, mocha, …) require shell=True to resolve
_SHELL = platform.system() == "Windows"

# ── Constants ─────────────────────────────────────────────────────────────────

THRESHOLD_DEFAULT  = 70
TIMEOUT_DEFAULT    = 60    # seconds per test run
LOGBOOK_DIR        = Path(".logbooks") / "mutation-testing"


# ── Baseline check ────────────────────────────────────────────────────────────

def baseline_passes(test_command: list[str], timeout: int) -> bool:
    """Return True if the test suite passes before any mutation."""
    try:
        result = subprocess.run(test_command, capture_output=True, timeout=timeout, shell=_SHELL)
        return result.returncode == 0
    except Exception:
        return False


# ── Apply / run / restore ─────────────────────────────────────────────────────

def _apply(file_path: Path, mutation: dict) -> tuple[str | None, str | None]:
    """
    Apply a single mutation. Returns (original_content, error_message).
    original_content is None if the file could not be read.
    error_message is None on success.
    """
    try:
        original = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        return None, f"read error: {exc}"

    lines = original.splitlines(keepends=True)
    idx = (mutation["line"] or 1) - 1

    if idx < 0 or idx >= len(lines):
        return None, f"line {mutation['line']} out of range ({len(lines)} lines total)"

    # Strip trailing whitespace for comparison to tolerate minor whitespace drift
    actual   = lines[idx].rstrip()
    expected = mutation["original_line"].rstrip()
    if actual != expected:
        return None, f"line mismatch"

    # Preserve original line ending
    if lines[idx].endswith("\r\n"):
        ending = "\r\n"
    elif lines[idx].endswith("\n"):
        ending = "\n"
    else:
        ending = ""

    lines[idx] = mutation["mutated_line"].rstrip() + ending

    try:
        file_path.write_text("".join(lines), encoding="utf-8")
    except Exception as exc:
        return original, f"write error: {exc}"

    return original, None


def _restore(file_path: Path, original: str) -> None:
    try:
        file_path.write_text(original, encoding="utf-8")
    except Exception as exc:
        print(f"\n  ⚠️  CRITICAL: failed to restore {file_path}: {exc}", file=sys.stderr)


def _run_tests(command: list[str], timeout: int) -> tuple[bool, str | None]:
    """Return (killed, error). killed=True means tests failed (mutation detected)."""
    try:
        result = subprocess.run(command, capture_output=True, timeout=timeout, shell=_SHELL)
        return result.returncode != 0, None
    except subprocess.TimeoutExpired:
        return True, "timeout"          # treat as killed
    except FileNotFoundError as exc:
        return False, f"runner not found: {exc}"
    except Exception as exc:
        return False, str(exc)


def run_mutation_loop(
    mutations: list[dict],
    test_command: list[str],
    cwd: Path,
    timeout: int,
) -> list[dict]:
    total = len(mutations)
    results: list[dict] = []

    for i, mutation in enumerate(mutations, 1):
        file_path = cwd / mutation["file"]
        label = f"[{i}/{total}] [{mutation['mutatorName']}] {mutation['file']}:{mutation['line']}"
        print(f"  {label}", end="", flush=True)

        original, apply_err = _apply(file_path, mutation)
        if apply_err:
            if original is not None:
                _restore(file_path, original)
            print(f"  ⏭  skip ({apply_err})")
            mutation["status"] = "Skipped"
            results.append(mutation)
            continue

        try:
            killed, run_err = _run_tests(test_command, timeout)
        finally:
            _restore(file_path, original)

        if run_err and run_err != "timeout":
            mutation["status"] = "Error"
            print(f"  ✗  error ({run_err})")
        elif killed:
            mutation["status"] = "Killed"
            print(f"  ✓  killed")
        else:
            mutation["status"] = "Survived"
            print(f"  ⚠  SURVIVED  ←  {mutation['replacement']}")

        results.append(mutation)

    return results


# ── Stats and output ──────────────────────────────────────────────────────────

def compute_stats(results: list[dict]) -> dict:
    killed = survived = errors = skipped = 0
    for m in results:
        match m.get("status"):
            case "Killed":   killed  += 1
            case "Survived": survived += 1
            case "Error":    errors  += 1
            case "Skipped":  skipped += 1

    total = killed + survived + errors   # skipped excluded from denominator
    score = round(100.0 * killed / total, 2) if total > 0 else 0.0

    return {
        "score":    score,
        "killed":   killed,
        "survived": survived,
        "errors":   errors,
        "skipped":  skipped,
        "total":    total,
    }


def extract_survivors(results: list[dict]) -> list[dict]:
    return [m for m in results if m.get("status") == "Survived"]


def print_summary(stats: dict, threshold: float) -> None:
    flag = "⚠️  BELOW THRESHOLD" if stats["score"] < threshold else "✅ OK"
    print()
    print("── Mutation Summary ──────────────────────────────")
    print(f"  Score:    {stats['score']}%  {flag}")
    print(f"  Killed:   {stats['killed']}")
    print(f"  Survived: {stats['survived']}")
    print(f"  Errors:   {stats['errors']}")
    print(f"  Skipped:  {stats['skipped']}")
    print(f"  Total:    {stats['total']}")
    print("──────────────────────────────────────────────────")
    print()


def print_gap_summary(gap_result: dict, stats: dict | None = None, has_logbook: bool = False) -> None:
    """Print new / persistent / fixed breakdown after a run."""
    new        = gap_result["new"]
    persistent = gap_result["persistent"]
    fixed      = gap_result["fixed"]
    survived   = (stats or {}).get("survived", 0)

    if not new and not persistent and not fixed:
        if survived == 0:
            print("✅ No surviving mutants.")
        elif has_logbook:
            print(f"🔕 {survived} survivor(s) acknowledged/wont_fix — no new or persistent gaps.")
        else:
            print(f"⚠️  {survived} survivor(s) — run with logbook enabled to track gaps.")
        return

    print()
    print("── Gap Summary ───────────────────────────────────")
    if new:
        print(f"  🆕 {len(new)} new gap(s) opened:")
        for m in new:
            print(f"     [{m['mutatorName']}] {m['file']}:{m.get('line')}  →  {m.get('replacement','')}")
            if m.get("rationale"):
                print(f"       {m['rationale']}")
    if persistent:
        print(f"  🔁 {len(persistent)} persistent gap(s) — still not covered:")
        for m in persistent:
            ts = m.get("times_survived", "?")
            print(f"     [{m['mutatorName']}] {m['file']}:{m.get('line')}  →  {m.get('replacement','')}  (survived {ts} run(s))")
    if fixed:
        print(f"  ✅ {len(fixed)} gap(s) fixed this run:")
        for m in fixed:
            print(f"     [{m['mutatorName']}] {m['file']}:{m.get('line')}  →  {m.get('replacement','')}")
    print("──────────────────────────────────────────────────")


def write_todos(stats: dict, threshold: float,
                gap_result: dict | None = None,
                conn: sqlite3.Connection | None = None,
                project: str = "") -> None:
    """Write mutation-todos.md from the full gap ledger when available,
    falling back to current-run survivors only."""
    flag = "⚠️ below threshold" if stats["score"] < threshold else "✅ above threshold"
    lines = [
        "# Mutation Testing — Open Gaps",
        "",
        f"**Score: {stats['score']}%** ({flag} of {threshold}%)"
        f"  |  Killed: {stats['killed']}  |  Survived: {stats['survived']}  |  Errors: {stats['errors']}",
        "",
    ]

    # Prefer full gap ledger over current-run-only survivors
    open_gaps: list[dict] = []
    if conn is not None and project:
        rows = conn.execute("""
            SELECT m.file, m.line, m.mutator, m.replacement, m.rationale,
                   m.times_survived, g.opened_at, g.status
            FROM gap_ledger g
            JOIN mutants m USING (mutant_key)
            WHERE m.project = ? AND g.status IN ('open', 'acknowledged')
            ORDER BY m.times_survived DESC, m.file, m.line
        """, (project,)).fetchall()
        open_gaps = [
            {"file": r[0], "line": r[1], "mutatorName": r[2], "replacement": r[3],
             "rationale": r[4], "times_survived": r[5], "opened_at": r[6], "gap_status": r[7]}
            for r in rows
        ]
    elif gap_result:
        # Fallback: just new + persistent from this run
        open_gaps = [
            {**m, "times_survived": m.get("times_survived", 1), "gap_status": "open"}
            for m in gap_result["new"] + gap_result["persistent"]
        ]

    if not open_gaps:
        lines.append("✅ No open gaps — test suite looks strong.\n")
    else:
        new_keys  = {mutant_key(m) for m in (gap_result or {}).get("new", [])}
        lines += [
            f"## {len(open_gaps)} Open Gap(s)",
            "",
            "| File | Line | Mutator | Change | Survived | Status | Why it matters |",
            "| ---- | ---- | ------- | ------ | -------- | ------ | -------------- |",
        ]
        for g in open_gaps:
            key    = mutant_key(g) if conn else ""
            badge  = "🆕 new" if key in new_keys else f"🔁 ×{g['times_survived']}"
            loc    = f"{g['file']}:{g['line']}"
            repl   = (g.get("replacement") or "").replace("|", "\\|")
            reason = (g.get("rationale")   or "").replace("|", "\\|")
            status = g.get("gap_status", "open")
            lines.append(f"| `{loc}` | {g['line']} | `{g['mutatorName']}` | `{repl}` | {badge} | {status} | {reason} |")

    Path("mutation-todos.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Logbook v2 ────────────────────────────────────────────────────────────────

def resolve_slug() -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True,
        )
        url  = result.stdout.strip()
        slug = url.rstrip("/").removesuffix(".git").split("/")[-1] or "project"
    except Exception:
        slug = Path.cwd().name
    return slug.lower().replace(" ", "-")


def resolve_git_context() -> dict:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        br  = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        st  = subprocess.run(["git", "status", "--porcelain"],
                             capture_output=True, text=True, timeout=5)
        return {
            "commit": sha.stdout.strip() or None,
            "branch": br.stdout.strip() or None,
            "dirty":  bool(st.stdout.strip()),
        }
    except Exception:
        return {"commit": None, "branch": None, "dirty": None}


def mutant_key(m: dict) -> str:
    # Includes mutated_line + col so two mutations on the same line with the same
    # mutator (e.g. two FlipGreaterThan variants) get distinct keys.
    raw = "\0".join([
        m.get("file", ""),
        str(m.get("line", "")),
        str(m.get("col", "")),
        m.get("mutatorName", ""),
        m.get("original_line", "").strip(),
        m.get("mutated_line", "").strip(),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def init_logbook(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id       TEXT PRIMARY KEY,
            project      TEXT NOT NULL,
            ran_at       TEXT NOT NULL,
            score        REAL NOT NULL,
            killed       INTEGER NOT NULL,
            survived     INTEGER NOT NULL,
            errors       INTEGER NOT NULL,
            skipped      INTEGER NOT NULL,
            total        INTEGER NOT NULL,
            threshold    REAL NOT NULL,
            passed       INTEGER NOT NULL,
            model        TEXT,
            test_command TEXT,
            timeout      INTEGER,
            commit       TEXT,
            branch       TEXT,
            dirty        INTEGER
        );
        CREATE TABLE IF NOT EXISTS mutants (
            mutant_key     TEXT PRIMARY KEY,
            project        TEXT NOT NULL,
            file           TEXT NOT NULL,
            line           INTEGER,
            col            INTEGER,
            mutator        TEXT NOT NULL,
            replacement    TEXT,
            original_line  TEXT,
            mutated_line   TEXT,
            rationale      TEXT,
            first_seen     TEXT NOT NULL,
            last_seen      TEXT NOT NULL,
            times_survived INTEGER NOT NULL DEFAULT 0,
            times_killed   INTEGER NOT NULL DEFAULT 0,
            last_status    TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mutant_results (
            run_id      TEXT NOT NULL REFERENCES runs(run_id),
            mutant_key  TEXT NOT NULL REFERENCES mutants(mutant_key),
            status      TEXT NOT NULL,
            PRIMARY KEY (run_id, mutant_key)
        );
        CREATE TABLE IF NOT EXISTS gap_ledger (
            mutant_key TEXT PRIMARY KEY REFERENCES mutants(mutant_key),
            status     TEXT NOT NULL CHECK(status IN ('open','acknowledged','fixed','wont_fix')),
            opened_at  TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            note       TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_mutant_results_run    ON mutant_results(run_id);
        CREATE INDEX IF NOT EXISTS idx_mutant_results_mutant ON mutant_results(mutant_key);
        CREATE INDEX IF NOT EXISTS idx_mutants_file          ON mutants(file);
        CREATE INDEX IF NOT EXISTS idx_gap_ledger_status     ON gap_ledger(status);
    """)
    # Migrate existing databases — SQLite has no ALTER TABLE ADD COLUMN IF NOT EXISTS
    for col, defn in [
        ("test_command", "TEXT"),
        ("timeout",      "INTEGER"),
        ("commit",       "TEXT"),
        ("branch",       "TEXT"),
        ("dirty",        "INTEGER"),
    ]:
        try:
            conn.execute(f"ALTER TABLE runs ADD COLUMN {col} {defn}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    return conn


def query_open_gaps(conn: sqlite3.Connection, project: str) -> list[dict]:
    """Return current open gaps from the ledger — used to surface prior context at run start."""
    rows = conn.execute("""
        SELECT m.file, m.line, m.mutator, m.replacement, m.times_survived,
               m.original_line, m.mutated_line, m.rationale, g.opened_at
        FROM gap_ledger g
        JOIN mutants m USING (mutant_key)
        WHERE g.status = 'open' AND m.project = ?
        ORDER BY m.times_survived DESC, m.file, m.line
    """, (project,)).fetchall()
    return [
        {
            "file": r[0], "line": r[1], "mutator": r[2], "replacement": r[3],
            "times_survived": r[4], "original_line": r[5], "mutated_line": r[6],
            "rationale": r[7], "opened_at": r[8],
        }
        for r in rows
    ]


def persist_run(
    conn: sqlite3.Connection,
    run_id: str,
    project: str,
    stats: dict,
    threshold: float,
    results: list[dict],
    model: str,
    run_ctx: dict,
) -> dict:
    """Persist a completed run. Returns gap categorisation: new/persistent/fixed + raw gap_updates."""
    now = datetime.now(timezone.utc).isoformat()
    gap_updates: list[dict] = []
    new_gaps:        list[dict] = []
    persistent_gaps: list[dict] = []
    fixed_gaps:      list[dict] = []

    dirty = run_ctx.get("dirty")
    conn.execute(
        "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            run_id, project, now,
            stats["score"], stats["killed"], stats["survived"],
            stats["errors"], stats["skipped"], stats["total"],
            threshold, 1 if stats["score"] >= threshold else 0,
            model,
            run_ctx.get("test_command"),
            run_ctx.get("timeout"),
            run_ctx.get("commit"),
            run_ctx.get("branch"),
            1 if dirty else 0 if dirty is not None else None,
        ),
    )

    for m in results:
        if m.get("status") == "Skipped":
            continue
        key   = mutant_key(m)
        status = m["status"]

        # Upsert mutant identity + aggregate counters
        existing = conn.execute(
            "SELECT times_survived, times_killed, first_seen FROM mutants WHERE mutant_key=?",
            (key,)
        ).fetchone()

        if existing:
            ts = existing[0] + (1 if status == "Survived" else 0)
            tk = existing[1] + (1 if status == "Killed"   else 0)
            conn.execute(
                "UPDATE mutants SET last_seen=?, times_survived=?, times_killed=?, last_status=? WHERE mutant_key=?",
                (run_id, ts, tk, status, key),
            )
        else:
            conn.execute(
                """INSERT INTO mutants
                   (mutant_key, project, file, line, col, mutator, replacement,
                    original_line, mutated_line, rationale,
                    first_seen, last_seen, times_survived, times_killed, last_status)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    key, project, m["file"], m.get("line"), m.get("col"),
                    m["mutatorName"], m.get("replacement", ""),
                    m.get("original_line", ""), m.get("mutated_line", ""),
                    m.get("rationale", ""),
                    run_id, run_id,
                    1 if status == "Survived" else 0,
                    1 if status == "Killed"   else 0,
                    status,
                ),
            )

        # Record result for this run
        conn.execute(
            "INSERT OR REPLACE INTO mutant_results (run_id, mutant_key, status) VALUES (?,?,?)",
            (run_id, key, status),
        )

        # Update gap ledger
        gap_row = conn.execute(
            "SELECT status FROM gap_ledger WHERE mutant_key=?", (key,)
        ).fetchone()
        gap_status = gap_row[0] if gap_row else None

        if status == "Survived":
            ts_row = conn.execute(
                "SELECT times_survived FROM mutants WHERE mutant_key=?", (key,)
            ).fetchone()
            ts = ts_row[0] if ts_row else 1

            if gap_status is None:
                conn.execute(
                    "INSERT INTO gap_ledger (mutant_key, status, opened_at, updated_at) VALUES (?,?,?,?)",
                    (key, "open", now, now),
                )
                gap_updates.append({"mutant_key": key, "old_status": None, "new_status": "open"})
                new_gaps.append({**m, "times_survived": ts})
            elif gap_status == "open":
                persistent_gaps.append({**m, "times_survived": ts})
            elif gap_status == "fixed":
                # Regression: a previously fixed gap is surviving again — reopen it
                conn.execute(
                    "UPDATE gap_ledger SET status='open', updated_at=?, note='reopened: survived again' WHERE mutant_key=?",
                    (now, key),
                )
                gap_updates.append({"mutant_key": key, "old_status": "fixed", "new_status": "open",
                                    "note": "reopened: survived again"})
                new_gaps.append({**m, "times_survived": ts})  # treat as new for visibility
            # acknowledged/wont_fix → leave ledger unchanged, don't surface
        elif status == "Killed" and gap_status == "open":
            conn.execute(
                "UPDATE gap_ledger SET status='fixed', updated_at=? WHERE mutant_key=?",
                (now, key),
            )
            gap_updates.append({"mutant_key": key, "old_status": "open", "new_status": "fixed"})
            fixed_gaps.append(m)

    conn.commit()
    return {
        "gap_updates": gap_updates,
        "new":         new_gaps,
        "persistent":  persistent_gaps,
        "fixed":       fixed_gaps,
    }


def append_jsonl(
    jsonl_path: Path,
    run_id: str,
    project: str,
    stats: dict,
    threshold: float,
    results: list[dict],
    model: str,
    gap_result: dict,
    now: str,
    run_ctx: dict,
) -> None:
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    dirty = run_ctx.get("dirty")
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps({
            "record_type":  "run",
            "run_id":       run_id,
            "project":      project,
            "ran_at":       now,
            "score":        stats["score"],
            "killed":       stats["killed"],
            "survived":     stats["survived"],
            "errors":       stats["errors"],
            "skipped":      stats["skipped"],
            "total":        stats["total"],
            "threshold":    threshold,
            "passed":       stats["score"] >= threshold,
            "model":        model,
            "test_command": run_ctx.get("test_command"),
            "timeout":      run_ctx.get("timeout"),
            "commit":       run_ctx.get("commit"),
            "branch":       run_ctx.get("branch"),
            "dirty":        1 if dirty else 0 if dirty is not None else None,
        }) + "\n")

        for m in results:
            if m.get("status") == "Skipped":
                continue
            f.write(json.dumps({
                "record_type": "mutant_result",
                "run_id":      run_id,
                "mutant_key":  mutant_key(m),
                "project":     project,
                "file":        m["file"],
                "line":        m.get("line"),
                "mutator":     m["mutatorName"],
                "replacement": m.get("replacement", ""),
                "status":      m["status"],
            }) + "\n")

        for gu in gap_result.get("gap_updates", []):
            f.write(json.dumps({
                "record_type": "gap_update",
                "mutant_key":  gu["mutant_key"],
                "project":     project,
                "old_status":  gu["old_status"],
                "new_status":  gu["new_status"],
                "note":        gu.get("note"),
                "updated_at":  now,
            }) + "\n")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Mutation testing runner: applies pre-generated mutations and runs the test suite.",
        epilog="--test-command must be the last flag; all remaining arguments become the command.",
    )
    parser.add_argument("--mutations-file", metavar="PATH", required=True,
                        help="JSON file of pre-generated mutations.")
    parser.add_argument("--threshold",    type=float, default=THRESHOLD_DEFAULT,
                        help=f"Minimum mutation score (default: {THRESHOLD_DEFAULT})")
    parser.add_argument("--timeout",      type=int,   default=TIMEOUT_DEFAULT,
                        help=f"Seconds per test run (default: {TIMEOUT_DEFAULT})")
    parser.add_argument("--model",        default=None,
                        help="Claude model used to generate the mutations — recorded in logbook only (optional)")
    parser.add_argument("--skip-baseline", action="store_true",
                        help="Skip the baseline test-suite pass check.")
    parser.add_argument("--no-logbook",   action="store_true",
                        help="Skip SQLite/JSONL logbook writes.")
    parser.add_argument("--test-command", nargs=argparse.REMAINDER, required=True,
                        help="Test command to run, e.g. python -m pytest --tb=no -q  "
                             "(must be the last flag — everything after it is captured).")
    args = parser.parse_args()

    if not args.test_command:
        print("❌ --test-command requires at least one argument.")
        sys.exit(1)

    cwd          = Path.cwd()
    test_command = args.test_command
    print(f"🧪 Test command: {' '.join(test_command)}")

    # ── Git context (captured before any file mutations) ──────────────────────
    git_ctx  = resolve_git_context()
    run_ctx  = {
        "test_command": " ".join(test_command),
        "timeout":      args.timeout,
        **git_ctx,
    }
    if git_ctx["dirty"]:
        print("⚠️  Git tree is dirty at run start — score is not reproducible.")

    # ── Baseline check ────────────────────────────────────────────────────────
    if not args.skip_baseline:
        print("⏱  Running baseline (tests must pass before mutation)…", end="", flush=True)
        if not baseline_passes(test_command, args.timeout):
            print()
            print("❌ Baseline test run failed — fix tests before running mutation testing.")
            print("   Use --skip-baseline to override.")
            sys.exit(1)
        print("  ✅")

    # ── Open logbook early (used for pre-run context + post-run writes) ───────
    conn        = None
    slug        = resolve_slug()
    db_path     = LOGBOOK_DIR / f"{slug}.sqlite"
    jsonl_path  = LOGBOOK_DIR / f"{slug}.jsonl"

    if not args.no_logbook:
        conn = init_logbook(db_path)
        known_gaps = query_open_gaps(conn, slug)
        if known_gaps:
            print(f"\n── Prior open gaps ({len(known_gaps)}) ─────────────────────────")
            for g in known_gaps[:5]:  # show top 5 by times_survived
                print(f"  🔁 [{g['mutator']}] {g['file']}:{g['line']}  ×{g['times_survived']} run(s)")
            if len(known_gaps) > 5:
                print(f"  … and {len(known_gaps) - 5} more")
            print("──────────────────────────────────────────────────")

    # ── Load mutations ────────────────────────────────────────────────────────
    print(f"\n📂 Loading mutations from {args.mutations_file}…")
    try:
        mutations = json.loads(Path(args.mutations_file).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"❌ Failed to load mutations file: {exc}")
        sys.exit(1)

    if not mutations:
        print("❌ No mutations in file.")
        sys.exit(1)
    print(f"✅ {len(mutations)} mutation(s) loaded")

    # ── Apply / run / restore loop ────────────────────────────────────────────
    print(f"\n🏃 Running mutation tests (timeout: {args.timeout}s each)…\n")
    results = run_mutation_loop(mutations, test_command, cwd, args.timeout)

    # ── Summary ───────────────────────────────────────────────────────────────
    stats = compute_stats(results)
    print_summary(stats, args.threshold)

    # ── All-skipped guard ─────────────────────────────────────────────────────
    if stats["total"] == 0 and stats["skipped"] > 0:
        print("⚠️  All mutations skipped — likely line-mismatch, not a test quality problem.")
        sys.exit(1)

    # ── Persist + gap summary ─────────────────────────────────────────────────
    gap_result: dict = {"new": [], "persistent": [], "fixed": [], "gap_updates": []}
    if conn is not None:
        now    = datetime.now(timezone.utc).isoformat()
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + f"-{secrets.token_hex(3)}-{slug}"
        gap_result = persist_run(conn, run_id, slug, stats, args.threshold, results, args.model, run_ctx)
        append_jsonl(jsonl_path, run_id, slug, stats, args.threshold, results, args.model, gap_result, now, run_ctx)
        print(f"📚 Logbook updated: {db_path}")

    print_gap_summary(gap_result, stats, has_logbook=conn is not None)

    # ── Write mutation-todos.md ───────────────────────────────────────────────
    write_todos(stats, args.threshold, gap_result=gap_result, conn=conn, project=slug)
    total_open = len(gap_result["new"]) + len(gap_result["persistent"])
    print(f"\n📝 mutation-todos.md written ({total_open} open gap(s) total)")

    if conn is not None:
        conn.close()

    # ── Threshold check ───────────────────────────────────────────────────────
    if stats["score"] < args.threshold:
        print(f"\n⚠️  Mutation score {stats['score']}% is below threshold {args.threshold}%")
        sys.exit(2)

    print(f"\n✅ Mutation score {stats['score']}% meets threshold {args.threshold}%")


if __name__ == "__main__":
    main()
