# mutation-testing

Validates test quality beyond coverage: uses Claude subagents to generate intelligent mutations for source code, runs them via the project's native test runner, and surfaces which behaviors your tests don't actually verify. Learn more at [agentlogbooks.com](https://agentlogbooks.com).

Tests pass ≠ tests are useful. A surviving mutant is a real bug the suite would miss. A run:

1. Discovers source files from project structure (or explicit globs).
2. Detects the test runner from config files (pytest, jest, vitest, mocha, go test).
3. Verifies the baseline test suite passes before mutating anything.
4. Dispatches one subagent per file in parallel to generate mutations.
5. Applies each mutation to disk, runs the test suite, restores the file.
6. Records `Killed` (detected) vs. `Survived` (missed — test gap).
7. Writes `mutation-todos.md` with a per-mutant rationale table.
8. Warns when the mutation score falls below 70% (exit code 2).

Each run is persisted to a per-project SQLite ledger and JSONL trace under `./.logbooks/mutation-testing/` in the repo, so follow-up runs can surface which gaps are new, persistent, or fixed.

## Install

### Claude Code (CLI)

```shell
/plugin marketplace add agentlogbooks/logbooks
/plugin install mutation-testing@logbooks
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
claude --plugin-dir ~/logbooks/plugins/mutation-testing
```

## Usage

Invoke from any repo with a working test suite:

```
/mutation-testing run mutation tests
/mutation-testing check mutation score
/mutation-testing are our tests actually testing anything?
/mutation-testing which tests are weak?
```

The skill generates mutations via subagents, runs them, and writes `mutation-todos.md` to the repo root with a table of survivors and why each one is a gap. No API key required — mutation generation is done by the calling Claude agent.

See the [root README](../../README.md) for the full plugin list.
