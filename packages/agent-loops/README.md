# Agent loops

Run the local loop with Node 24+:

```sh
node --experimental-strip-types packages/agent-loops/src/cli.ts \
  --repository bacluc-agent/agent-runner \
  --issue-repository bacluc-agent/agent-todo
```

The reusable packages are `@bacluc-agent/github` and `@bacluc-agent/steps`.
The provisioned `agent-loops` launcher runs all three phases repeatedly and
uses a fresh devcontainer workspace for every agent invocation.

The default is one sequential refine, hourly, and review cycle. Use `--repeat`, `--cycles`, `--poll`, `--phases`, or `--dry-run` to control it. `BACLUC_AGENT_GITHUB_TOKEN` is read from the environment and is passed to the devcontainer only through its environment, never through a command argument. Each agent invocation gets a fresh `/tmp/agent-loops-*` workspace and is removed after the invocation.

Each phase selects its model independently. `--model` takes precedence, then
`MODEL`, then the availability list using the workflow order and deny list. A
dry run performs only GitHub reads, skips provider probing and label changes,
and emits lifecycle lines without prompts or agent output.

Automatic model selection reads `scripts/model-deny-list.txt`, or the path in
`MODEL_DENY_LIST_FILE`, using the same patterns as the workflows.
