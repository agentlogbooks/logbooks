# ideation

Idea-centric brainstorming on a per-topic SQLite logbook. Learn more at [agentlogbooks.com](https://agentlogbooks.com).

Atomic operators (`generate`, `transform`, `evaluate`, `validate`, `decide`) compose into playbooks — covering brainstorming, naming, developing or combining ideas, stress-testing candidates, reframing problems, and picking final directions. Ideas persist across sessions, so follow-up prompts resume where the last one ended.

A logbook lives at `./.logbooks/ideation/<topic-slug>/logbook.sqlite` under your current repo root (or cwd). It carries the topic's frame, facts, ideas, lineage, assessments, and operator runs — the authoritative state across sessions.

## Install

### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbooks
/plugin install ideation@logbooks
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
claude --plugin-dir ~/logbooks/plugins/ideation
```

## Usage

Start or continue ideation on a topic. Slug is lowercase alphanumeric with dashes or underscores:

```
/ideation coffee-shop-q2: brainstorm ways to grow afternoon revenue
/ideation coffee-shop-q2: develop idea 17 further
/ideation product: what should we call this product
/ideation shortlist --playbook stress_test_shortlist: validate the top 3
```

Other shapes:

```
/ideation --list-topics                      # list existing topics
/ideation <slug> --show-state                # dump topic state (no plan, no ops)
/ideation <slug> --no-checkpoints: <intent>  # autonomous run, strip checkpoints
```

Default for a fresh topic is a lightweight flow (frame + ~20 ideas + a compare report). Opt in to deeper shapes with explicit intent — "thorough" / "deep" for the full treatment, "score them" / "prioritize" for a scored pass, "name X" for the naming playbook.

See the [root README](../../README.md) for the full plugin list.
