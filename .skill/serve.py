import http.server, socketserver, time, socket, sys
from pathlib import Path

ROOT   = Path(__file__).parent
EVENTS = ROOT.parent / ".skill-events.jsonl"
PORT   = 7878

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/health":
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        elif path == "/":
            html = (ROOT / "view.html").read_bytes()
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
            offset = 0
            try:
                while True:
                    if EVENTS.exists():
                        with EVENTS.open(encoding="utf-8") as f:
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

def port_free(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False

if not port_free(PORT):
    print(f"Port {PORT} already in use — server may already be running.", file=sys.stderr)
    sys.exit(0)

print(f"Live dashboard → http://127.0.0.1:{PORT}", flush=True)
ThreadedServer(("127.0.0.1", PORT), Handler).serve_forever()
