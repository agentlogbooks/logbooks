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


_REQUIRED_TOP_LEVEL = (
    "name",
    "stage",
    "scope",
    "applies_to",
    "use_when",
    "avoid_when",
    "produces",
    "cost",
    "repeat_guard",
    "followups",
)


def lint_operator(
    meta: dict[str, Any],
    filename: str,
    known_operator_names: set[str] | None = None,
) -> list[str]:
    """Return a list of human-readable lint errors; empty list means clean."""
    errors: list[str] = []

    # Check required fields first; subsequent checks depend on them.
    for field in _REQUIRED_TOP_LEVEL:
        if field not in meta:
            errors.append(f"missing required field: {field}")
    if errors:
        return errors

    name = meta["name"]
    expected_filename = f"{name}.md"
    if filename != expected_filename:
        errors.append(f"filename {filename!r} does not match name.md {expected_filename!r}")

    stage = meta["stage"]
    if stage not in VALID_STAGES:
        errors.append(f"stage {stage!r} not in {VALID_STAGES}")
    else:
        prefix = name.split(".", 1)[0] if "." in name else ""
        if prefix != stage:
            errors.append(f"stage {stage!r} does not match name prefix {prefix!r}")

    scope = meta["scope"]
    if scope not in VALID_SCOPES:
        errors.append(f"scope {scope!r} not in {VALID_SCOPES}")

    applies_to = meta["applies_to"]
    if not isinstance(applies_to, dict):
        errors.append("applies_to must be a mapping")
    else:
        kinds = applies_to.get("kinds")
        if not isinstance(kinds, list):
            errors.append("applies_to.kinds must be a list")
        else:
            for k in kinds:
                if k not in VALID_KINDS:
                    errors.append(f"applies_to.kinds has invalid kind {k!r}")
        min_cohort = applies_to.get("min_cohort")
        if not isinstance(min_cohort, int) or min_cohort < 1:
            errors.append("applies_to.min_cohort must be an integer >= 1")

    for field in ("use_when", "avoid_when", "followups"):
        if not isinstance(meta[field], list):
            errors.append(f"{field} must be a list of strings")

    produces = meta["produces"]
    if not isinstance(produces, dict) or not all(
        isinstance(produces.get(k), bool) for k in ("ideas", "assessments", "facts")
    ):
        errors.append("produces must be {ideas: bool, assessments: bool, facts: bool}")
    else:
        if stage == "transform" and not produces["ideas"]:
            errors.append("transform.* operators must have produces.ideas: true")
        if stage == "validate":
            if not produces["facts"]:
                errors.append("validate.* operators must have produces.facts: true")
            if not produces["assessments"]:
                errors.append("validate.* operators must have produces.assessments: true")
        if stage == "evaluate" and not produces["assessments"]:
            errors.append("evaluate.* operators must have produces.assessments: true")
        if stage == "frame" and produces["ideas"]:
            errors.append("frame.* operators must have produces.ideas: false")

    cost = meta["cost"]
    if not isinstance(cost, dict) or not isinstance(cost.get("web"), bool):
        errors.append("cost must be {web: bool}")

    repeat_guard = meta["repeat_guard"]
    cooldown = repeat_guard.get("same_lineage_cooldown") if isinstance(repeat_guard, dict) else None
    if not isinstance(cooldown, int) or cooldown < 0:
        errors.append("repeat_guard.same_lineage_cooldown must be an integer >= 0")
    elif scope == "pool" and cooldown != 0:
        errors.append("scope: pool requires repeat_guard.same_lineage_cooldown: 0")

    if known_operator_names is not None:
        for fn in meta["followups"]:
            if fn not in known_operator_names:
                errors.append(f"followups references unknown operator: {fn}")

    return errors


def load_catalog(operators_dir: Path) -> list[dict[str, Any]]:
    """Parse + lint every operator file. Raises on first failure."""
    raw: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(operators_dir.glob("*.md")):
        text = path.read_text()
        try:
            meta = parse_frontmatter(text)
        except FrontmatterError as e:
            raise FrontmatterError(f"{path.name}: {e}") from e
        raw.append((path.name, meta))

    known_names = {m["name"] for _, m in raw if "name" in m}
    for filename, meta in raw:
        errs = lint_operator(meta, filename, known_operator_names=known_names)
        if errs:
            raise LintError(f"{filename}:\n  - " + "\n  - ".join(errs))

    return [m for _, m in raw]


def operators_dir_default() -> Path:
    """Default location of the operators/ directory (sibling of scripts/)."""
    return Path(__file__).resolve().parent.parent / "operators"
