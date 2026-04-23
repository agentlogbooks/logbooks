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
4. Enter `agentlogbooks/logbooks` and click **Sync**

**In Cowork mode:**

1. Click **Customize** in the left sidebar
2. Next to **Personal plugins**, click **"+"** → **Add marketplace**
3. Enter `agentlogbooks/logbooks` and click **Sync**

**Upload manually:**

1. Go to [github.com/agentlogbooks/logbooks](https://github.com/agentlogbooks/logbooks) → green **Code** button → **Download ZIP**
2. Rename the file from `.zip` to `.plugin`
3. In the same plugin menu above, choose **Upload plugin** instead and select the file

### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbooks
/plugin install logbook-creator@logbooks
/plugin install deep-code-review@logbooks
/plugin install ideation@logbooks
```

Or from a local clone:

```bash
git clone https://github.com/agentlogbooks/logbooks.git ~/logbooks
claude --plugin-dir ~/logbooks/plugins/logbook-creator
```

## Skills

| Plugin | Skill | What it does |
|---|---|---|
| `logbook-creator` | `/logbook-creator` | Design and create a logbook — a shared, queryable, schema-stable working surface for agents and humans to append, annotate, and query across sessions. |
| `deep-code-review` | `/deep-code-review` | Hotspot-first deep code review: change map → risky hotspot selection → per-hotspot lens subagents → skeptic pass → comment budget. Surfaces at most 5 high-signal findings or questions per run. |
| `ideation` | `/ideation` | Idea-centric brainstorming on a per-topic SQLite logbook. Atomic operators (generate, transform, evaluate, validate, decide) compose into playbooks. Covers brainstorming, naming, developing or combining ideas, stress-testing candidates, reframing, and picking final directions. Ideas persist across sessions — follow-up prompts resume where the last one ended. |

## Usage

### logbook-creator

Ask Claude to create a logbook when you need to track structured entries across sessions, stage drafts before pushing to a target system, or coordinate state between agents. Invoke the skill directly with:

```
/logbook-creator
```

Claude will walk you through the motivation, schema, and storage choice, then write the logbook file and a sibling spec describing it.

### deep-code-review

Run a hotspot-first code review on a PR, branch, or diff:

```
/deep-code-review review PR #42
/deep-code-review review current branch changes
```

The skill maps behavior changes, selects risky hotspots, runs per-hotspot analysis, applies a skeptic pass, and surfaces at most 5 high-signal findings or questions. Results are persisted to a per-PR JSONL trace and SQLite ledger at `./.logbooks/code-review/` in the reviewed repo.

### ideation

Start or continue ideation on a topic:

```
/ideation coffee-shop-q2: brainstorm ways to grow afternoon revenue
/ideation coffee-shop-q2: develop idea 17 further
/ideation product: what should we call this product
/ideation shortlist --playbook stress_test_shortlist: validate the top 3
```

Default for a fresh topic is a lightweight flow (frame + ~20 ideas + a compare report). Opt in to deeper shapes with explicit intent — "thorough" / "deep" for the full treatment, "score them" / "prioritize" for a scored pass, "name X" for the naming playbook. Logbooks live at `./.logbooks/ideation/<slug>/logbook.sqlite` and persist across sessions, so follow-up prompts on the same slug pick up where the last one ended.
