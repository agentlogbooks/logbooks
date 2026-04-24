import json, sys, time
from pathlib import Path
EVENTS = Path(__file__).parent.parent / ".skill-events.jsonl"
payload = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
event = {"ts": time.time(), "type": sys.argv[1], "payload": payload}
with open(EVENTS, "a", encoding="utf-8") as f:
    f.write(json.dumps(event) + "\n")
