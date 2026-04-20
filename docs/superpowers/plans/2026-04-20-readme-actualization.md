# README Actualization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully rewrite `README.md` to reflect the repo rename to `logbooks`, reframe the intro as a collection of logbook-backed Claude skills, fix all install commands, and update the deep-code-review description to v2.

**Architecture:** Single file edit (`README.md`) organized into four sections: header/intro, skills table, install, usage. No code, no tests — each task edits one section and commits.

**Tech Stack:** Markdown, git

---

## File Structure

- Modify: `README.md` (full rewrite, section by section)

---

### Task 1: Rewrite header and intro

**Files:**
- Modify: `README.md` (lines 1–3)

- [ ] **Step 1: Replace the title and intro paragraph**

Replace the current opening:

```markdown
# logbook-creator

A Claude plugin that helps you design and create a logbook — a shared, queryable, schema-stable working surface that agents and humans append to, annotate, and query across sessions.
```

With:

```markdown
# logbooks

Logbooks are shared working state: structured entries that agents and humans can append, patch, annotate, query, and carry forward across sessions. Learn more at [agentlogbooks.com](https://agentlogbooks.com).

This repo is a collection of Claude skills that use logbooks as their working surface.
```

- [ ] **Step 2: Verify the file opens correctly**

Open `README.md` and confirm the first three lines match the new content exactly.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): update title and intro for logbooks collection"
```

---

### Task 2: Rewrite Skills section

**Files:**
- Modify: `README.md` (the `## Plugins` section, currently lines 44–51)

- [ ] **Step 1: Replace the Plugins section with a Skills section**

Replace:

```markdown
## Plugins

This repo contains two plugins:

| Plugin | Skill | What it does |
|---|---|---|
| `logbook-creator` | `/logbook-creator` | Design and create a logbook — a shared, queryable, schema-stable working surface for agents and humans to append, annotate, and query across sessions. |
| `deep-code-review` | `/deep-code-review` | Multi-phase deep code review: detect angles → research best practices → parallel subagent review → deduplicate → score findings by severity × confidence. |
```

With:

```markdown
## Skills

| Plugin | Skill | What it does |
|---|---|---|
| `logbook-creator` | `/logbook-creator` | Design and create a logbook — a shared, queryable, schema-stable working surface for agents and humans to append, annotate, and query across sessions. |
| `deep-code-review` | `/deep-code-review` | Hotspot-first deep code review: change map → risky hotspot selection → per-hotspot lens subagents → skeptic pass → comment budget. Surfaces at most 5 high-signal findings or questions per run. |
```

Note: the section title changes from "Plugins" to "Skills", the preamble sentence is removed (the table is self-explanatory), and the `deep-code-review` description is updated to match v2.0.0 (`plugin.json`).

- [ ] **Step 2: Verify the table renders correctly**

Check that the table has exactly two rows and that the `deep-code-review` description no longer mentions "detect angles" or "severity × confidence".

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): rename Plugins→Skills, update deep-code-review to v2 description"
```

---

### Task 3: Rewrite Setup section — Claude Desktop

**Files:**
- Modify: `README.md` (the `### Claude Desktop` subsection, currently lines 7–28)

- [ ] **Step 1: Update the marketplace entry string**

In both **In Chat mode** and **In Cowork mode** subsections, replace:

```
Enter `agentlogbooks/logbook-creator` and click **Sync**
```

With:

```
Enter `agentlogbooks/logbooks` and click **Sync**
```

(Two occurrences — one in each mode subsection.)

- [ ] **Step 2: Update the manual upload link and URL**

Replace:

```markdown
1. Go to [github.com/agentlogbooks/logbook-creator](https://github.com/agentlogbooks/logbook-creator) → green **Code** button → **Download ZIP**
```

With:

```markdown
1. Go to [github.com/agentlogbooks/logbooks](https://github.com/agentlogbooks/logbooks) → green **Code** button → **Download ZIP**
```

- [ ] **Step 3: Verify all occurrences of the old repo name are gone from this section**

Search the Claude Desktop section for `logbook-creator` — there should be zero remaining occurrences.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): update Claude Desktop install to agentlogbooks/logbooks"
```

---

### Task 4: Rewrite Setup section — Claude Code CLI

**Files:**
- Modify: `README.md` (the `### Claude Code (CLI)` subsection, currently lines 30–42)

- [ ] **Step 1: Replace the CLI install commands**

Replace:

```markdown
### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbook-creator
/plugin install logbook-creator@agentlogbooks-logbook-creator
```

Or from a local clone:

```bash
git clone https://github.com/agentlogbooks/logbook-creator.git ~/logbook-creator
claude --plugin-dir ~/logbook-creator
```
```

With:

```markdown
### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbooks
/plugin install logbook-creator@logbooks
/plugin install deep-code-review@logbooks
```

Or from a local clone:

```bash
git clone https://github.com/agentlogbooks/logbooks.git ~/logbooks
claude --plugin-dir ~/logbooks/plugins/logbook-creator
```
```

Key changes:
- `agentlogbooks/logbook-creator` → `agentlogbooks/logbooks` (GitHub repo renamed)
- `logbook-creator@agentlogbooks-logbook-creator` → `logbook-creator@logbooks` (`@` token is the marketplace `name` field, which is `"logbooks"` in `marketplace.json`)
- Added `deep-code-review@logbooks` install line
- Clone URL updated to `logbooks.git`
- `--plugin-dir` now points to `~/logbooks/plugins/logbook-creator` (the plugin subdirectory, not the marketplace root)

- [ ] **Step 2: Verify the section**

Confirm there are no remaining references to `logbook-creator` in URLs or install commands in this section. The word `logbook-creator` should only appear as a plugin name argument in `/plugin install logbook-creator@logbooks`.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): fix Claude Code CLI install commands for logbooks rename"
```

---

### Task 5: Update Usage section — deep-code-review

**Files:**
- Modify: `README.md` (the `### deep-code-review` subsection, currently lines 65–74)

- [ ] **Step 1: Update the deep-code-review usage description**

Replace:

```markdown
### deep-code-review

Run a deep multi-angle code review on a PR, branch, or diff:

```
/deep-code-review review PR #42
/deep-code-review review current branch changes
```

Findings are scored by severity × confidence and persisted to a per-PR SQLite + JSONL logbook at `~/logbooks/code-review/`.
```

With:

```markdown
### deep-code-review

Run a hotspot-first code review on a PR, branch, or diff:

```
/deep-code-review review PR #42
/deep-code-review review current branch changes
```

The skill maps behavior changes, selects risky hotspots, runs per-hotspot analysis, applies a skeptic pass, and surfaces at most 5 high-signal findings or questions. Results are persisted to a per-PR JSONL trace and SQLite ledger at `~/logbooks/code-review/`.
```

- [ ] **Step 2: Verify the usage section**

Confirm "multi-angle", "severity × confidence", and "scored" are no longer present in the deep-code-review usage block.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs(readme): update deep-code-review usage to v2 pipeline description"
```

---

### Task 6: Final review pass

**Files:**
- Read: `README.md`

- [ ] **Step 1: Scan for any remaining old repo name references**

Search `README.md` for `logbook-creator` — only valid occurrences are:
- Plugin name in the Skills table: `` `logbook-creator` ``
- Plugin install argument: `logbook-creator@logbooks`
- Section heading: `### logbook-creator`
- Plugin dir path: `~/logbooks/plugins/logbook-creator`

Any other occurrence is a bug — fix it before committing.

- [ ] **Step 2: Scan for stale v1 deep-code-review language**

Search for: `detect angles`, `research best practices`, `parallel subagent`, `severity × confidence`, `multi-angle`. All should be absent.

- [ ] **Step 3: Verify agentlogbooks.com is linked in the intro**

Confirm the intro paragraph contains `[agentlogbooks.com](https://agentlogbooks.com)`.

- [ ] **Step 4: Read the full README end-to-end**

Render mentally or preview in a markdown viewer. Check that it reads coherently as a collection README, not a single-plugin README.

- [ ] **Step 5: Commit if any fixes were made**

```bash
git add README.md
git commit -m "docs(readme): fix remaining stale references in final review pass"
```

If no fixes were needed, skip this commit.
