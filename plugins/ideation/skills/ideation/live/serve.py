#!/usr/bin/env python3
"""
Ideation live-wall server.

Usage:
    python plugins/ideation/skills/ideation/live/serve.py <topic-slug>

Serves the React "Ideation Dashboard" at http://127.0.0.1:7878 and exposes:

  GET /            → dashboard shell (view.html) + its JS modules
  GET /state       → full session snapshot as JSON, projected from the
                     authoritative SQLite logbook and overlaid with the
                     live event stream (which op is running, the plan,
                     checkpoints, completion). This is what the dashboard
                     renders.
  GET /events      → SSE stream of raw live events. The dashboard uses it
                     only as a "something changed, re-fetch /state" trigger,
                     so no session state is lost if a tab connects mid-run.

The logbook is read strictly read-only; the server never writes to it.
"""

import http.server, socketserver, time, socket, sys, json, argparse, sqlite3
from datetime import datetime
from pathlib import Path

THIS_DIR = Path(__file__).parent
PORT = 7878

# Static files the dashboard shell loads, with their content types. Only these
# paths are served from disk — everything else 404s.
STATIC_FILES = {
    "/": ("view.html", "text/html; charset=utf-8"),
    "/view.html": ("view.html", "text/html; charset=utf-8"),
    "/views.jsx": ("views.jsx", "text/babel; charset=utf-8"),
    "/live-data.jsx": ("live-data.jsx", "text/babel; charset=utf-8"),
    "/app.jsx": ("app.jsx", "text/babel; charset=utf-8"),
}

# operator-name prefix → dashboard phase id
PHASE_OF_PREFIX = {
    "frame": "frame",
    "generate": "generate",
    "transform": "transform",
    "evaluate": "evaluate",
    "validate": "evaluate",
    "decide": "decide",
}


def logbook_path(slug: str) -> Path:
    return Path(".logbooks") / "ideation" / slug / "logbook.sqlite"


def events_path(slug: str) -> Path:
    return Path(".logbooks") / "ideation" / slug / "live-events.jsonl"


def _loads(text, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def _phase_of(operator_name: str) -> str:
    return PHASE_OF_PREFIX.get((operator_name or "").split(".", 1)[0], "generate")


def _duration(started_at, ended_at):
    if not started_at or not ended_at:
        return None
    try:
        dt = (datetime.fromisoformat(ended_at) - datetime.fromisoformat(started_at)).total_seconds()
        return round(dt, 1) if dt >= 0 else None
    except ValueError:
        return None


def read_events(slug: str) -> dict:
    """Fold the append-only event log into the live overlay the DB can't supply:
    the plan, which ops are mid-flight, an open checkpoint, and completion."""
    overlay = {
        "PLAN": [],
        "running_op_ids": [],
        "op_descriptions": {},   # op_run_id → plan-step prose (label for in-flight ops)
        "checkpoint": None,
        "complete": False,
        "started_at": None,      # epoch seconds of the first event
    }
    evf = events_path(slug)
    if not evf.exists():
        return overlay

    started, finished = set(), set()
    try:
        with evf.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                etype, p = ev.get("type"), ev.get("payload") or {}
                if overlay["started_at"] is None and ev.get("ts"):
                    overlay["started_at"] = ev["ts"]
                if etype == "plan_set":
                    overlay["PLAN"] = [
                        {
                            "n": s.get("n"),
                            "label": s.get("description", ""),
                            "checkpoint": s.get("type") == "checkpoint",
                            "parallel": s.get("type") == "parallel",
                        }
                        for s in (p.get("steps") or [])
                    ]
                elif etype == "op_started":
                    oid = p.get("op_run_id")
                    if oid is not None:
                        started.add(oid)
                        if p.get("description"):
                            overlay["op_descriptions"][oid] = p["description"]
                elif etype == "op_finished":
                    if p.get("op_run_id") is not None:
                        finished.add(p["op_run_id"])
                elif etype == "checkpoint_reached":
                    overlay["checkpoint"] = {"name": p.get("name"), "step_n": p.get("step_n")}
                elif etype == "checkpoint_resolved":
                    overlay["checkpoint"] = None
                elif etype == "session_complete":
                    overlay["complete"] = True
    except OSError:
        return overlay

    overlay["running_op_ids"] = sorted(started - finished)
    return overlay


def build_state(slug: str) -> dict:
    """Project the SQLite logbook + event overlay into the dashboard's
    IDEATION model. Always returns a valid (possibly empty) snapshot."""
    overlay = read_events(slug)
    running = set(overlay["running_op_ids"])
    op_desc = overlay["op_descriptions"]

    state = {
        "TOPIC": {"slug": slug, "description": "", "owner": ""},
        "FRAME": None,
        "IDEAS": [],
        "ASSESSMENTS": [],
        "OPERATOR_RUNS": [],
        "PLAN": overlay["PLAN"],
        "checkpoint": overlay["checkpoint"],
        "complete": overlay["complete"],
        "startedAt": overlay["started_at"],
    }

    db = logbook_path(slug)
    if not db.exists():
        return state

    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return state

    try:
        meta = conn.execute(
            "SELECT description, owner FROM topic_meta WHERE topic_slug=?", (slug,)
        ).fetchone()
        if meta:
            state["TOPIC"]["description"] = meta["description"] or ""
            state["TOPIC"]["owner"] = meta["owner"] or ""

        frame = conn.execute(
            "SELECT frame_id, version, problem_statement, root_causes, hmw_questions, "
            "triz_contradiction FROM frames WHERE active=1 ORDER BY frame_id DESC LIMIT 1"
        ).fetchone()
        if frame:
            state["FRAME"] = {
                "frame_id": frame["frame_id"],
                "version": frame["version"],
                "problem_statement": frame["problem_statement"],
                "root_causes": _loads(frame["root_causes"], []),
                "hmw_questions": _loads(frame["hmw_questions"], []),
                "triz_contradiction": _loads(frame["triz_contradiction"], None),
            }

        # parent edges: child_id → [parent_id, ...]
        parents = {}
        for r in conn.execute(
            "SELECT child_idea_id, parent_idea_id FROM lineage ORDER BY parent_idea_id"
        ):
            parents.setdefault(r["child_idea_id"], []).append(r["parent_idea_id"])

        for r in conn.execute(
            "SELECT idea_id, title, description, kind, tag, temperature_zone, status, "
            "score_summary, origin_operator_run_id FROM ideas ORDER BY idea_id"
        ):
            state["IDEAS"].append({
                "id": r["idea_id"],
                "title": r["title"],
                "desc": r["description"],
                "kind": r["kind"],
                "tag": r["tag"],
                "zone": r["temperature_zone"],
                "status": r["status"],
                "score": r["score_summary"],
                "origin": r["origin_operator_run_id"],
                "parents": parents.get(r["idea_id"], []),
            })

        for r in conn.execute(
            "SELECT idea_id, metric, value_numeric, rationale, operator_run_id "
            "FROM assessments WHERE value_numeric IS NOT NULL ORDER BY assessment_id"
        ):
            state["ASSESSMENTS"].append({
                "idea": r["idea_id"],
                "metric": r["metric"],
                "value": r["value_numeric"],
                "rationale": r["rationale"],
                "run": r["operator_run_id"],
            })

        # produced-idea ids per op
        produces = {}
        for r in conn.execute(
            "SELECT origin_operator_run_id AS op, idea_id FROM ideas ORDER BY idea_id"
        ):
            produces.setdefault(r["op"], []).append(r["idea_id"])

        for r in conn.execute(
            "SELECT operator_run_id, plan_step_index, operator_name, operator_persona, "
            "cohort_ids, status, outcome_summary, started_at, ended_at "
            "FROM operator_runs ORDER BY operator_run_id"
        ):
            oid = r["operator_run_id"]
            db_status = r["status"]
            # the DB can't tell 'currently running' from 'not yet started' (both
            # are 'pending') — the event stream resolves it.
            status = "running" if (oid in running and db_status == "pending") else db_status
            label = r["outcome_summary"] or op_desc.get(oid) or r["operator_name"]
            state["OPERATOR_RUNS"].append({
                "id": oid,
                "phase": _phase_of(r["operator_name"]),
                "name": r["operator_name"],
                "persona": r["operator_persona"],
                "label": label,
                "cohort": _loads(r["cohort_ids"], []),
                "produces": produces.get(oid, []),
                "status": status,
                "step_n": r["plan_step_index"],
                "duration": _duration(r["started_at"], r["ended_at"]),
            })
    except sqlite3.Error:
        pass
    finally:
        conn.close()

    return state


class Handler(http.server.BaseHTTPRequestHandler):
    slug: str = ""

    def log_message(self, fmt, *args):
        pass

    def _send(self, body: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/health":
            self._send(b"ok", "text/plain")
            return

        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return

        if path == "/state":
            try:
                body = json.dumps(build_state(self.slug)).encode("utf-8")
                self._send(body, "application/json; charset=utf-8")
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            return

        if path in STATIC_FILES:
            fname, ctype = STATIC_FILES[path]
            try:
                self._send((THIS_DIR / fname).read_bytes(), ctype)
            except OSError:
                self._send(b"not found", "text/plain", 404)
            return

        if path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            evf = events_path(self.slug)
            offset = 0
            try:
                while True:
                    if evf.exists():
                        with evf.open(encoding="utf-8") as f:
                            f.seek(offset)
                            for line in f:
                                line = line.strip()
                                if line:
                                    self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
                                    self.wfile.flush()
                            offset = f.tell()
                    time.sleep(0.2)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            return

        self._send(b"not found", "text/plain", 404)


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="Topic slug, e.g. logbooks-plugin")
    args = ap.parse_args()

    if not port_free(PORT):
        print(f"Port {PORT} already in use — server may already be running.", file=sys.stderr)
        sys.exit(0)

    Handler.slug = args.slug
    print(f"Topic:     {args.slug}")
    print(f"Logbook:   {logbook_path(args.slug)}")
    print(f"Events:    {events_path(args.slug)}")
    print(f"Dashboard: http://127.0.0.1:{PORT}", flush=True)
    ThreadedServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
