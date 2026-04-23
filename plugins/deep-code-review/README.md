# deep-code-review

Hotspot-first, multi-pass code review for pull requests, branches, pasted diffs, and work-in-progress changes. Learn more at [agentlogbooks.com](https://agentlogbooks.com).

Optimized to be **right about a few important things**, not to produce many comments. A run:

1. Models behavior changes from the diff.
2. Selects risky hotspots.
3. Acquires minimal local context per hotspot.
4. Generates candidate findings and questions.
5. Runs a skeptic pass and dedup.
6. Surfaces **at most 5** high-signal outputs.

Each run is persisted to a per-run JSONL trace and per-PR SQLite ledger under `./.logbooks/code-review/` in the reviewed repo, so follow-up reviews can see what was already flagged.

## Install

### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbooks
/plugin install deep-code-review@logbooks
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
claude --plugin-dir ~/logbooks/plugins/deep-code-review
```

## Usage

Run a review on a PR, branch, or diff:

```
/deep-code-review review PR #42
/deep-code-review review current branch changes
/deep-code-review check this diff
/deep-code-review audit this repo
```

The skill will **not** engage for vague opinion requests with no concrete target ("what do you think of these changes?", "any concerns?") — give it a diff, a PR number, or a branch.

Outputs are either `finding` (likely true, actionable) or `question` (high-impact uncertainty to confirm). Formatting-only changes, trivial renames, import reorderings, generated files, and speculative style comments are ignored by default.

See the [root README](../../README.md) for the full plugin list.
