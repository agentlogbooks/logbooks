# AI Mutation Generation Reference

How Claude generates mutations, model tradeoffs, prompt caching, and tuning guidance.

---

## How it works

For each source file the script sends a single API call to Claude:

1. **System prompt** (cached) — instructs Claude on which mutation types to generate and what to skip
2. **User message** — contains the file path and line-numbered source content
3. **Tool use** — Claude calls `report_mutations` to return structured JSON; the script never parses free-form text

The tool schema enforces the shape of each mutation:

```json
{
  "id": "m1",
  "mutator_name": "FlipGreaterThan",
  "line": 14,
  "original_line": "    if score > threshold:",
  "mutated_line":  "    if score >= threshold:",
  "replacement":   "> → >=",
  "rationale":     "Tests may not cover the boundary case where score equals threshold exactly"
}
```

`original_line` and `mutated_line` are complete lines with leading whitespace preserved so the
script can apply and verify the mutation without re-parsing the file.

---

## Prompt caching

The system prompt is marked `cache_control: ephemeral`. When the script processes multiple source
files in sequence, the system prompt is cached on the first call and reused for all subsequent
calls in the same session — avoiding re-tokenizing the same instructions for every file.

Cache hits are visible in the API response under `usage.cache_read_input_tokens`.

---

## Model tradeoffs

| Model | Strength | Best for |
| ----- | -------- | -------- |
| `claude-opus-4-7` (default) | Deepest code understanding, most creative mutations, best rationale | Large codebases, complex logic, when mutation quality matters most |
| `claude-sonnet-4-6` | Fast, cheaper, still strong | CI pipelines, many files, iterative runs |
| `claude-haiku-4-5-20251001` | Fastest, cheapest | Quick smoke runs, very large file counts |

Override with `--model`:

```bash
python mutation_testing.py --model claude-sonnet-4-6
```

---

## Mutation types generated

| Category | Examples |
| -------- | -------- |
| Conditional operators | `>` → `>=`, `==` → `!=`, `<` → `<=`, `and` → `or` |
| Boolean negation | `x` → `not x`, `True` → `False`, `is None` → `is not None` |
| Arithmetic operators | `+` → `-`, `*` → `/` |
| Return values | `return x + 1` → `return x`, `return value` → `return None` |
| String literals | `"text"` → `""` |
| Boundary values | `0` → `1`, `-1` → `0`, `n` → `n + 1` |
| Argument removal/swap | `f(a, b)` → `f(a)`, `f(a, b)` → `f(b, a)` |

Lines skipped: comments, imports, type annotations, docstrings, blank lines, logging.

---

## Tuning guidance

### Too many mutations (slow runs)

Reduce with `--max-per-file`:

```bash
python mutation_testing.py --max-per-file 5
```

Or restrict to critical files:

```bash
python mutation_testing.py --sources "src/core/**/*.py"
```

### Skipped mutations (line mismatch)

Skipped means Claude's `original_line` didn't match the actual file content (after stripping
trailing whitespace). Common causes:

- Claude added or removed trailing whitespace
- The file uses CRLF line endings inconsistently
- Claude hallucinated a line that doesn't exist

Skipped mutants are logged to stdout and excluded from the score. If skip rates are high, try
`claude-opus-4-7` which tends to be more precise about line content.

### Baseline always fails

If `--skip-baseline` is needed regularly, the test suite has a pre-existing failure. Fix that
first — mutation testing on a broken suite produces meaningless results.

### Timeout errors

Increase `--timeout` (default 60s):

```bash
python mutation_testing.py --timeout 120
```

Or add `--max-per-file 3` to reduce total run time.

---

## Environment

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `ANTHROPIC_API_KEY` | Yes | Authenticates Claude API calls |
| `ANTHROPIC_BASE_URL` | No | Override for proxies or internal endpoints |

The script uses `anthropic.Anthropic()` which reads `ANTHROPIC_API_KEY` automatically.
