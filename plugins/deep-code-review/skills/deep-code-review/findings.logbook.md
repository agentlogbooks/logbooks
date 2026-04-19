---
schema_version: 1
# schema_version must match evals/evals.json schema_version — bump both together when the schema changes
scope: solo-cross-machine
bindings:
  # GOVERNANCE: This file is a shared repo artifact — permanently read-only once committed.
  # Never edit any address or status field here. Store resolved IDs and status:active
  # in a local-only override (e.g. a gitignored ~/logbooks/code-review/bindings.local.yaml
  # or env vars). Agents must never write back to this file.
  # Per-PR file backends — {slug} is replaced with the PR ref (e.g. pr-123) at runtime
  - driver: sqlite
    address_pattern: ~/logbooks/code-review/{slug}.sqlite
    note: creates both `angles` and `findings` tables; {slug} resolved per PR/session at runtime
  - driver: jsonl
    address_pattern: ~/logbooks/code-review/{slug}.jsonl
    note: mixed record_type (angle | finding); {slug} resolved per PR/session at runtime
  # Cloud backends — shared across PRs; pr_ref + date stored as columns
  - driver: airtable
    label: angles
    address: airtable://appPLACEHOLDER/tblANGLES_PLACEHOLDER?pat_env=AIRTABLE_PAT
    status: pending-auth
  - driver: airtable
    label: findings
    address: airtable://appPLACEHOLDER/tblFINDINGS_PLACEHOLDER?pat_env=AIRTABLE_PAT
    status: pending-auth
  - driver: google_sheets
    label: angles
    address: gsheets://SPREADSHEET_ID_PLACEHOLDER/angles?gws_account=PLACEHOLDER
    status: pending-auth
  - driver: google_sheets
    label: findings
    address: gsheets://SPREADSHEET_ID_PLACEHOLDER/findings?gws_account=PLACEHOLDER
    status: pending-auth

# Primary schema: findings table
# Cloud bindings also include pr_ref + date (encoded in filename for file backends)
columns:
  # findings table
  - name: id
    type: integer
    note: auto-increment primary key
  - name: angle_id
    type: integer
    note: FK → angles.id (file backends); cloud bindings embed angle_name/source/description instead
  - name: finding
    type: text
  - name: file_path
    type: text
    nullable: true
  - name: line_ref
    type: text
    nullable: true
    note: e.g. "42-57"
  - name: severity
    type: enum
    values: [info, low, medium, high, critical]
  - name: confidence
    type: real
    not_null: true
    constraint: "BETWEEN 0.0 AND 1.0"
    note: 0.0–1.0, AI confidence in the finding
  - name: score
    type: integer
    not_null: true
    constraint: "BETWEEN 0 AND 100"
    note: 0–100, final weighted score (severity × confidence)
  - name: status
    type: enum
    values: [new, duplicate-logbook, duplicate-pr, addressed]
  - name: duplicate_ref
    type: text
    nullable: true
    note: logbook finding ID or PR comment URL
  - name: agent_model
    type: text
    note: model that produced this finding, e.g. claude-sonnet-4-6
  # cloud-only columns (omitted from file backends — encoded in filename)
  - name: pr_ref
    type: text
    note: cloud backends only; e.g. "pr-123" or "session-20260418"
  - name: date
    type: date
    note: cloud backends only; ISO 8601

# Angles table schema (secondary — documented separately because it is a related table, not a column of findings)
angles_schema:
  - name: id
    type: integer
    note: auto-increment primary key
  - name: name
    type: text
    not_null: true
    unique: true
    note: e.g. security, maintainability, correctness, data-integrity; UNIQUE enforced in DDL
  - name: description
    type: text
    not_null: true
    note: what this angle examines
  - name: source
    type: enum
    not_null: true
    values: [always-on, heuristic, web-researched, user-defined]
    note: user-defined = angle requested explicitly by the user, bypasses heuristic detection
  - name: research_notes
    type: text
    nullable: true
    note: best practices summary from web research phase; null for always-on and special-rule angles

---

## Purpose

Per-PR (or per-session) structured store for deep code review findings produced by a multi-phase agent pipeline. Each review run detects angles, augments them with researched best practices, runs one subagent per angle, deduplicates findings against the existing logbook and live PR comments, then scores findings by severity and confidence. The logbook persists findings across sessions so patterns can be spotted across PRs over time.

Two backends are active immediately (SQLite and JSONL, one file per PR); two cloud backends (Airtable, Google Sheets) are wired but pending auth setup.

## Tables

### angles

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | Auto-increment |
| name | text | e.g. `security`, `maintainability`, `correctness` |
| description | text | What this angle examines |
| source | enum | `always-on / heuristic / web-researched / user-defined` |
| research_notes | text | Best practices found in web research phase; nullable for always-on |

**Always-on angles** (inserted first in every review run):
- `maintainability` — Code clarity, naming, modularity, technical debt, ease of future change
- `correctness` — Logic errors, edge cases, off-by-one, null handling, incorrect assumptions

### findings

| Column | Type | Notes |
|--------|------|-------|
| id | integer PK | Auto-increment |
| angle_id | integer FK | References `angles.id` |
| finding | text | The finding |
| file_path | text | Nullable |
| line_ref | text | e.g. `"42-57"`, nullable |
| severity | enum | `info / low / medium / high / critical` |
| confidence | real | 0.0–1.0, AI confidence in the finding |
| score | integer | 0–100, final weighted score (`round(severity_weight × confidence × 100)`) |
| status | enum | `new / duplicate-logbook / duplicate-pr / addressed` |
| duplicate_ref | text | Logbook finding ID or PR comment URL, nullable |
| agent_model | text | Model that produced the finding |
| pr_ref | text | **Cloud backends only** — encoded in filename for file backends |
| date | date | **Cloud backends only** — encoded in filename for file backends |

**Severity weights** (for score computation):
| severity | weight |
|----------|--------|
| critical | 1.0 |
| high | 0.8 |
| medium | 0.5 |
| low | 0.2 |
| info | 0.05 |

**Cloud backends** use denormalized angle columns (`angle_name`, `angle_source`, `angle_description`) instead of `angle_id` FK.

## Pipeline phases

1. **Angle detection** — analyse the diff/PR to identify relevant review dimensions. Always add `maintainability` and `correctness`. Add heuristic angles based on what the code touches (auth → security, DB queries → data-integrity, public API → api-design, etc.).
2. **Angle augmentation** — for each non-always-on angle, web-search for known best practices and store the summary in `research_notes`.
3. **Subagent review** — one subagent per angle reads the diff/PR plus `research_notes`, produces findings with `severity` and `confidence`.
4. **Deduplication** — mark findings as `duplicate-logbook` if a near-identical finding exists in this logbook for the same PR; mark `duplicate-pr` if a matching comment already exists on the PR (via `gh pr view --comments`).
5. **Scoring** — compute `score = round(severity_weight × confidence × 100)`. Sort findings descending by score.

## Queries

### SQLite (per-PR file, e.g. pr-123)

**Initialize a new PR review** (run once per PR):
```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite "
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS angles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL,
  source TEXT NOT NULL CHECK(source IN ('always-on','heuristic','web-researched','user-defined')),
  research_notes TEXT
);
CREATE TABLE IF NOT EXISTS findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  angle_id INTEGER NOT NULL REFERENCES angles(id),
  finding TEXT NOT NULL,
  file_path TEXT,
  line_ref TEXT,
  severity TEXT NOT NULL CHECK(severity IN ('info','low','medium','high','critical')),
  confidence REAL NOT NULL CHECK(confidence BETWEEN 0.0 AND 1.0),
  score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
  status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new','duplicate-logbook','duplicate-pr','addressed')),
  duplicate_ref TEXT,
  agent_model TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_findings_angle_id ON findings(angle_id);
"
```

**Insert always-on angles:**
```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite "
INSERT INTO angles (name, description, source) VALUES
  ('maintainability', 'Code clarity, naming, modularity, technical debt, ease of future change', 'always-on'),
  ('correctness', 'Logic errors, edge cases, off-by-one, null handling, incorrect assumptions', 'always-on');
"
```

**Insert a finding:**
```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite \
  "INSERT INTO findings (angle_id, finding, file_path, line_ref, severity, confidence, score, status, agent_model)
   VALUES (1, 'Missing null check on user input', 'src/auth.ts', '42', 'high', 0.9, 72, 'new', 'claude-sonnet-4-6');"
```

**Top findings by score:**
```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite \
  "SELECT f.score, f.severity, a.name AS angle, f.finding, f.file_path, f.line_ref
   FROM findings f JOIN angles a ON f.angle_id = a.id
   WHERE f.status = 'new'
   ORDER BY f.score DESC LIMIT 20;"
```

**Findings by angle:**
```bash
sqlite3 ~/logbooks/code-review/pr-123.sqlite \
  "SELECT a.name, COUNT(*) AS count, AVG(f.score) AS avg_score
   FROM findings f JOIN angles a ON f.angle_id = a.id
   GROUP BY a.name ORDER BY avg_score DESC;"
```

### JSONL (per-PR file)

**Append an angle record:**
```bash
echo '{"record_type":"angle","id":1,"name":"security","description":"Auth, injection, data exposure, secrets","source":"heuristic","research_notes":"OWASP Top 10 recommends..."}' \
  >> ~/logbooks/code-review/pr-123.jsonl
```

**Append a finding record** (include `pr_ref` and `date` in JSONL even though they're encoded in the filename — makes records self-describing if extracted to a cloud backend later):
```bash
python3 -c "
import json, datetime
record = {'record_type':'finding','id':1,'angle_id':1,'finding':'API key logged in plaintext',
          'file_path':'src/client.ts','line_ref':'88','severity':'critical','confidence':0.95,
          'score':95,'status':'new','duplicate_ref':'','agent_model':'claude-sonnet-4-6',
          'pr_ref':'pr-123','date':str(datetime.date.today())}
print(json.dumps(record))
" >> ~/logbooks/code-review/pr-123.jsonl
```

**Top findings by score:**
```bash
grep '"record_type":"finding"' ~/logbooks/code-review/pr-123.jsonl \
  | jq -s 'sort_by(-.score) | .[] | {score, severity, finding, file_path}'
```

**Count findings per angle:**
```bash
grep '"record_type":"finding"' ~/logbooks/code-review/pr-123.jsonl \
  | jq -s 'group_by(.angle_id) | map({angle_id: .[0].angle_id, count: length, avg_score: (map(.score) | add / length)})'
```

### Airtable (shared, pending-auth)

Once `status: active` — append a finding:
```bash
curl -X POST "https://api.airtable.com/v0/appPLACEHOLDER/tblFINDINGS_PLACEHOLDER" \
  -H "Authorization: Bearer $AIRTABLE_PAT" \
  -H "Content-Type: application/json" \
  -d '{"fields": {"pr_ref": "pr-123", "date": "'"$(date -I)"'", "angle_name": "security", "angle_source": "heuristic", "angle_description": "Auth, injection, secrets", "finding": "API key logged", "severity": "critical", "confidence": 0.95, "score": 95, "status": "new", "agent_model": "claude-sonnet-4-6"}}'
```

Top findings for a PR:
```bash
curl "https://api.airtable.com/v0/appPLACEHOLDER/tblFINDINGS_PLACEHOLDER?filterByFormula=\{pr_ref\}='pr-123'&sort[0][field]=score&sort[0][direction]=desc&maxRecords=20" \
  -H "Authorization: Bearer $AIRTABLE_PAT"
```

### Google Sheets (shared, pending-auth)

Once `status: active` — append a finding:
```bash
gws sheets spreadsheets values append \
  --params '{"spreadsheetId":"SPREADSHEET_ID_PLACEHOLDER","range":"findings!A1","valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"}' \
  --json '{"values":[["pr-123","'"$(date -I)"'","security","heuristic","API key logged","","","critical","0.95","95","new","","claude-sonnet-4-6"]]}'
```

Query last 20:
```bash
gws sheets spreadsheets values get \
  --params '{"spreadsheetId":"SPREADSHEET_ID_PLACEHOLDER","range":"findings!A1:M21"}'
# Columns A–M: pr_ref, date, angle_name, angle_source, finding, file_path, line_ref, severity, confidence, score, status, duplicate_ref, agent_model
```
