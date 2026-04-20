# README Actualization Design

**Date:** 2026-04-20
**Scope:** Full restructure of `README.md` in the `logbooks` repo

---

## Goals

1. Reflect the repo rename from `logbook-creator` to `logbooks` in all appropriate places.
2. Reframe the intro from single-plugin focus to collection-of-skills framing, linking to agentlogbooks.com.
3. Update `deep-code-review` description to v2.0.0 (hotspot-first pipeline).
4. Fix all install commands and URLs.
5. Make the skills table scalable for future plugins.

---

## What does NOT change

- Skill invocations: `/logbook-creator`, `/deep-code-review` — these are determined by the skill folder name inside each plugin, not the repo name.
- Plugin names: `logbook-creator`, `deep-code-review`.
- Usage instructions content (how to invoke each skill, what it does step by step).

---

## Document structure

### 1. Header + intro

```markdown
# logbooks

Logbooks are shared working state: structured entries that agents and humans
can append, patch, annotate, query, and carry forward across sessions.
Learn more at [agentlogbooks.com](https://agentlogbooks.com).

This repo is a collection of Claude skills that use logbooks as their working surface.
```

Source for the logbooks definition: the agentlogbooks.com site (`index.html` hero lead paragraph).

### 2. Skills table

| Plugin | Skill | What it does |
|---|---|---|
| `logbook-creator` | `/logbook-creator` | Design and create a logbook — a shared, queryable, schema-stable working surface for agents and humans to append, annotate, and query across sessions. |
| `deep-code-review` | `/deep-code-review` | Hotspot-first deep code review: change map → risky hotspot selection → per-hotspot lens subagents → skeptic pass → comment budget. Surfaces at most 5 high-signal findings or questions per run. |

Description text sourced directly from each plugin's `plugin.json`.

The table is left open-ended (no "more coming" note) — new rows are added as new plugins land.

### 3. Install section

Framing: install once, use any skill. One `marketplace add` command installs the full repo; then install individual plugins by name.

#### Claude Desktop

Steps updated to use `agentlogbooks/logbooks` (was `agentlogbooks/logbook-creator`). Chat and Cowork sub-sections preserved as-is structurally. Manual upload steps updated with new repo URL.

#### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbooks
/plugin install logbook-creator@logbooks
/plugin install deep-code-review@logbooks
```

- `agentlogbooks/logbooks` = GitHub owner/repo (renamed).
- `@logbooks` = marketplace `name` field in `marketplace.json` (already `"logbooks"` — was wrong in old README as `agentlogbooks-logbook-creator`).

Local clone:

```bash
git clone https://github.com/agentlogbooks/logbooks.git ~/logbooks
claude --plugin-dir ~/logbooks/plugins/logbook-creator
```

(Was pointing at wrong path — old README used `~/logbook-creator` directly, which is a marketplace root, not a plugin directory.)

### 4. Usage section

One subsection per skill, same as current README. Changes:

- `deep-code-review`: update description paragraph to reflect v2 — hotspot-first pipeline, at most 5 high-signal findings or questions. Keep the invocation examples (`/deep-code-review review PR #42`, etc.) unchanged.
- `logbook-creator`: no changes to usage content.

---

## Identifiers reference

| Identifier | Old value | New value | Determined by |
|---|---|---|---|
| GitHub repo URL | `agentlogbooks/logbook-creator` | `agentlogbooks/logbooks` | GitHub repo name |
| Marketplace add arg | `agentlogbooks/logbook-creator` | `agentlogbooks/logbooks` | GitHub repo name |
| Plugin install token | `logbook-creator@agentlogbooks-logbook-creator` | `logbook-creator@logbooks` | `marketplace.json` name field |
| Local clone path | `~/logbook-creator` | `~/logbooks` | convention |
| `--plugin-dir` path | `~/logbook-creator` | `~/logbooks/plugins/logbook-creator` | plugin subdirectory |
| Skill invocation | `/logbook-creator`, `/deep-code-review` | unchanged | skill folder name |
| Plugin names | `logbook-creator`, `deep-code-review` | unchanged | `plugin.json` name field |
