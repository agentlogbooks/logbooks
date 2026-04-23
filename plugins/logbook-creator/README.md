# logbook-creator

Design and create a **logbook** — a shared, queryable, schema-stable working surface that agents and humans append to, annotate, and query across sessions. Learn more at [agentlogbooks.com](https://agentlogbooks.com).

The skill runs a guided conversation through motivation, schema, storage format, identity rule, and governance, then writes two artifacts:

- **A logbook instance** — the actual storage (CSV, JSONL, SQLite, spreadsheet, or markdown table) with the schema in place.
- **A logbook spec** — a sibling markdown file (`<logbook-name>.logbook.md`) describing schema semantics, identity rule, partial-row convention, correction rule, query patterns, validation rules, actions, and governance.

This plugin creates the logbook and its spec — it does not write SKILL.md files. Hand off to `skill-creator` afterward to wire the logbook into a skill.

## Install

### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbooks
/plugin install logbook-creator@logbooks
```

### Claude Desktop

Works in both **Chat** and **Cowork** modes.

**In Chat mode:**

1. Click **Customize** in the left sidebar
2. Open the **Directory** and select the **Plugins** tab
3. Switch to the **Personal** tab, click **"+"** → **Add marketplace**
4. Enter `agentlogbooks/logbooks` and click **Sync**

**In Cowork mode:**

1. Click **Customize** in the left sidebar
2. Next to **Personal plugins**, click **"+"** → **Add marketplace**
3. Enter `agentlogbooks/logbooks` and click **Sync**

**Upload manually:**

1. Go to [github.com/agentlogbooks/logbooks](https://github.com/agentlogbooks/logbooks) → green **Code** button → **Download ZIP**
2. Rename the file from `.zip` to `.plugin`
3. In the same plugin menu above, choose **Upload plugin** instead and select the file

### Local clone

```bash
git clone https://github.com/agentlogbooks/logbooks.git ~/logbooks
claude --plugin-dir ~/logbooks/plugins/logbook-creator
```

## Usage

Invoke the skill directly:

```
/logbook-creator
```

Or let Claude invoke it when you describe the intent:

```
I want to track design decisions across sessions — agents propose, I review.
Let me stage Jira candidates before pushing to Jira for real.
Two agents need to share findings and scores on the same entries.
```

Claude walks you through the motivation, schema, identity rule, and storage choice, then writes the logbook file and its spec. See the [root README](../../README.md) for the full plugin list.
