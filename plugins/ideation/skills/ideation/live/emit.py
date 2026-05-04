#!/usr/bin/env python3
"""
Emit a single event to the ideation live wall.

Usage:
    python plugins/ideation/skills/ideation/live/emit.py <type> '<json-payload>' <topic-slug>

Examples:
    python ...emit.py session_started '{"topic":"my-topic","phases":["Frame","Generate","Decide"]}' my-topic
    python ...emit.py idea_generated '{"id":1,"title":"...","description":"...","kind":"seed","tag":"BOLD","status":"active"}' my-topic
    python ...emit.py phase_started '{"name":"Generate"}' my-topic
    python ...emit.py session_complete '{}' my-topic
"""

import json, sys, time
from pathlib import Path

if len(sys.argv) < 4:
    print(f"Usage: emit.py <type> '<json>' <slug>", file=sys.stderr)
    sys.exit(1)

event_type = sys.argv[1]
payload    = json.loads(sys.argv[2])
slug       = sys.argv[3]

events_file = Path(".logbooks") / "ideation" / slug / "live-events.jsonl"
events_file.parent.mkdir(parents=True, exist_ok=True)

event = {"ts": time.time(), "type": event_type, "payload": payload}
with open(events_file, "a", encoding="utf-8") as f:
    f.write(json.dumps(event) + "\n")
