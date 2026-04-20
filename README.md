# logbooks

Logbooks are shared working state: structured entries that agents and humans can append, patch, annotate, query, and carry forward across sessions. Learn more at [agentlogbooks.com](https://agentlogbooks.com).

This repo is a collection of Claude skills that use logbooks as their working surface.

## Setup

### Claude Desktop

Works in both **Chat** and **Cowork** modes — the plugin installs once and is available everywhere.

**In Chat mode:**

1. Click **Customize** in the left sidebar
2. Open the **Directory** and select the **Plugins** tab
3. Switch to the **Personal** tab, click **"+"** → **Add marketplace**
4. Enter `agentlogbooks/logbook-creator` and click **Sync**

**In Cowork mode:**

1. Click **Customize** in the left sidebar
2. Next to **Personal plugins**, click **"+"** → **Add marketplace**
3. Enter `agentlogbooks/logbook-creator` and click **Sync**

**Upload manually:**

1. Go to [github.com/agentlogbooks/logbook-creator](https://github.com/agentlogbooks/logbook-creator) → green **Code** button → **Download ZIP**
2. Rename the file from `.zip` to `.plugin`
3. In the same plugin menu above, choose **Upload plugin** instead and select the file

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

## Skills

| Plugin | Skill | What it does |
|---|---|---|
| `logbook-creator` | `/logbook-creator` | Design and create a logbook — a shared, queryable, schema-stable working surface for agents and humans to append, annotate, and query across sessions. |
| `deep-code-review` | `/deep-code-review` | Hotspot-first deep code review: change map → risky hotspot selection → per-hotspot lens subagents → skeptic pass → comment budget. Surfaces at most 5 high-signal findings or questions per run. |

## Usage

### logbook-creator

Ask Claude to create a logbook when you need to track structured entries across sessions, stage drafts before pushing to a target system, or coordinate state between agents. Invoke the skill directly with:

```
/logbook-creator
```

Claude will walk you through the motivation, schema, and storage choice, then write the logbook file and a sibling spec describing it.

### deep-code-review

Run a deep multi-angle code review on a PR, branch, or diff:

```
/deep-code-review review PR #42
/deep-code-review review current branch changes
```

Findings are scored by severity × confidence and persisted to a per-PR SQLite + JSONL logbook at `~/logbooks/code-review/`.
