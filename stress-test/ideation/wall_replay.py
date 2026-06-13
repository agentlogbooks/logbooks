#!/usr/bin/env python3
"""
wall_replay.py — reusable stress/replay harness for the ideation live wall.

Serves ANY view HTML file and replays ANY captured (or synthetic) event stream
over the same `/events` SSE contract the real `live/serve.py` uses. This lets you:

  * eyeball the wall under bursts / large volumes / failures without running a
    real (minutes-long) ideation session, and
  * A/B the current `view.html` against a prototype by pointing `--html` at each.

Usage:
    python wall_replay.py --events scenarios/state_80.jsonl \
        --html ../../plugins/ideation/skills/ideation/live/view.html \
        --port 7879 --cadence 0

    # "live feel" replay with a fixed 250ms gap between events:
    python wall_replay.py --events scenarios/timeline.jsonl --cadence 0.25

Event file format is identical to `.logbooks/ideation/<slug>/live-events.jsonl`:
one JSON object per line: {"ts": <float>, "type": "<event>", "payload": {...}}.
So you can also replay a REAL session:
    python wall_replay.py --events .logbooks/ideation/<slug>/live-events.jsonl

`--cadence 0` dumps every event on connect (snapshot / hydrate behaviour — best
for deterministic screenshots). A positive cadence streams them one-by-one.
"""
import argparse
import http.server
import socket
import socketserver
import sys
import time
from pathlib import Path

PORT = 7879


class Handler(http.server.BaseHTTPRequestHandler):
    html_path: Path = None
    events_path: Path = None
    cadence: float = 0.0

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        elif path == "/":
            html = self.html_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        elif path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                lines = []
                if self.events_path.exists():
                    lines = [l.strip() for l in self.events_path.read_text(encoding="utf-8").splitlines() if l.strip()]
                for line in lines:
                    self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    if self.cadence > 0:
                        time.sleep(self.cadence)
                # hold the connection so EventSource doesn't reconnect-loop
                while True:
                    time.sleep(1.0)
                    self.wfile.write(b": keep-alive\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
        else:
            self.send_response(404); self.end_headers()


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def main():
    here = Path(__file__).parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(here / "scenarios" / "state_20.jsonl"))
    ap.add_argument("--html", default=str(here.parent.parent /
                    "plugins/ideation/skills/ideation/live/view.html"))
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--cadence", type=float, default=0.0,
                    help="seconds between events; 0 = dump all on connect (snapshot)")
    args = ap.parse_args()

    Handler.html_path = Path(args.html).resolve()
    Handler.events_path = Path(args.events).resolve()
    Handler.cadence = args.cadence

    if not Handler.html_path.exists():
        sys.exit(f"ERROR: html not found: {Handler.html_path}")
    if not port_free(args.port):
        sys.exit(f"ERROR: port {args.port} already in use")

    print(f"HTML:     {Handler.html_path}")
    print(f"Events:   {Handler.events_path}")
    print(f"Cadence:  {args.cadence}s")
    print(f"Wall:     http://127.0.0.1:{args.port}", flush=True)
    ThreadedServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
