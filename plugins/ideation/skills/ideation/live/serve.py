#!/usr/bin/env python3
"""
Ideation live-wall server.

Usage:
    python plugins/ideation/skills/ideation/live/serve.py <topic-slug>

Reads events from .logbooks/ideation/<slug>/live-events.jsonl and streams
them over SSE to the browser at http://127.0.0.1:7878.
"""

import http.server, socketserver, time, socket, sys, argparse
from pathlib import Path

THIS_DIR = Path(__file__).parent
PORT = 7878

def events_path(slug: str) -> Path:
    return Path(".logbooks") / "ideation" / slug / "live-events.jsonl"


class Handler(http.server.BaseHTTPRequestHandler):
    slug: str = ""

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        elif path == "/":
            html = (THIS_DIR / "view.html").read_bytes()
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
        else:
            self.send_response(404); self.end_headers()


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
    evf = events_path(args.slug)
    print(f"Topic:     {args.slug}")
    print(f"Events:    {evf}")
    print(f"Dashboard: http://127.0.0.1:{PORT}", flush=True)
    ThreadedServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
