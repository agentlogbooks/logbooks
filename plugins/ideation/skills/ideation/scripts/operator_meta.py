"""
operator_meta.py — frontmatter parsing, linting, and catalog loading for
ideation operators. Pure stdlib; no PyYAML dependency.

Frontmatter grammar is deliberately narrow — only the exact shape
specified in the ideation-operator-routing design doc is accepted.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

VALID_STAGES = ("frame", "generate", "transform", "evaluate", "validate", "decide")
VALID_SCOPES = ("per_idea", "pair", "group", "pool")
VALID_KINDS = ("seed", "variant", "hybrid", "refinement", "counter")

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


class FrontmatterError(ValueError):
    pass


class LintError(ValueError):
    pass


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Parse the leading YAML-ish frontmatter block from a markdown file."""
    m = _FM_RE.match(text)
    if not m:
        raise FrontmatterError("missing or malformed `---` frontmatter block at top of file")
    body = m.group(1)
    return _parse_block(body)


def _parse_block(block: str) -> dict[str, Any]:
    """Parse one frontmatter block into a nested dict."""
    return _parse_lines(block.splitlines(), indent=0)[0]


def _parse_lines(lines: list[str], indent: int) -> tuple[dict[str, Any], int]:
    """Parse lines at the given indent level; return (dict, next_line_index)."""
    out: dict[str, Any] = {}
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.lstrip().startswith("#"):
            i += 1
            continue
        # Enforce space-only indentation (reject tabs in leading whitespace).
        stripped = raw.lstrip()
        leading = raw[: len(raw) - len(stripped)]
        if any(ch != " " for ch in leading):
            raise FrontmatterError(f"non-space indent character at line: {raw!r}")
        cur_indent = len(leading)
        if cur_indent < indent:
            return out, i
        if cur_indent > indent:
            raise FrontmatterError(f"unexpected indent at line: {raw!r}")
        if ":" not in raw:
            raise FrontmatterError(f"expected 'key:' line, got: {raw!r}")
        key, _, rest = raw.strip().partition(":")
        if not key:
            raise FrontmatterError(f"empty key in line: {raw!r}")
        if key in out:
            raise FrontmatterError(f"duplicate key {key!r}")
        rest = rest.strip()
        if rest == "":
            # Block value — either a list (next line starts with `-`) or a nested dict.
            sub_start = i + 1
            if sub_start < len(lines) and lines[sub_start].lstrip().startswith("-"):
                items, consumed = _parse_list(lines[sub_start:], indent + 2)
                out[key] = items
                i = sub_start + consumed
            else:
                sub, consumed = _parse_lines(lines[sub_start:], indent + 2)
                out[key] = sub
                i = sub_start + consumed
        else:
            out[key] = _parse_scalar_or_inline_list(rest)
            i += 1
    return out, i


def _parse_list(lines: list[str], indent: int) -> tuple[list[Any], int]:
    """Parse a block list (one `- item` per line at the given indent)."""
    out: list[Any] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip():
            i += 1
            continue
        # Enforce space-only indentation (reject tabs in leading whitespace).
        stripped = raw.lstrip()
        leading = raw[: len(raw) - len(stripped)]
        if any(ch != " " for ch in leading):
            raise FrontmatterError(f"non-space indent character at line: {raw!r}")
        cur_indent = len(leading)
        if cur_indent < indent:
            return out, i
        if not stripped.startswith("-"):
            return out, i
        item = stripped[1:].strip()
        out.append(_parse_scalar_or_inline_list(item))
        i += 1
    return out, i


_INLINE_LIST_RE = re.compile(r"\A\[(.*)\]\Z")


def _parse_scalar_or_inline_list(text: str) -> Any:
    """Parse a scalar (string/int/bool) or an inline list `[a, b, c]`."""
    if text == "":
        return ""
    m = _INLINE_LIST_RE.match(text)
    if m:
        inner = m.group(1).strip()
        if inner == "":
            return []
        return [_parse_scalar(p.strip()) for p in inner.split(",")]
    return _parse_scalar(text)


def _parse_scalar(text: str) -> Any:
    if text == "true":
        return True
    if text == "false":
        return False
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def lint_operator(meta: dict[str, Any], filename: str) -> list[str]:
    """Return a list of human-readable lint errors; empty list means clean."""
    # Implemented in Task 3.
    return []


def load_catalog(operators_dir: Path) -> list[dict[str, Any]]:
    """Load and parse every operators/*.md file. Raises if any fails."""
    # Implemented in Task 4.
    entries: list[dict[str, Any]] = []
    for path in sorted(operators_dir.glob("*.md")):
        text = path.read_text()
        try:
            meta = parse_frontmatter(text)
        except FrontmatterError as e:
            raise FrontmatterError(f"{path.name}: {e}") from e
        entries.append(meta)
    return entries
