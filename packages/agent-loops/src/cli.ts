#!/usr/bin/env -S node --experimental-strip-types
import {
  parsePhases,
  resolveLauncher,
  run,
  type LoopOptions,
} from "./index.ts";

function value(
  args: string[],
  name: string,
  fallback?: string,
): string | undefined {
  const index = args.indexOf(name);
  return index < 0 ? fallback : args[index + 1];
}

const args = process.argv.slice(2);
if (args.includes("--help")) {
  console.log(
    "agent-loops --repository OWNER/REPO --issue-repository OWNER/REPO [--cycles N] [--repeat] [--poll SECONDS] [--phases refine,hourly,review] [--dry-run]",
  );
  process.exit(0);
}

const repository = value(args, "--repository", process.cwd())!;
const issueRepository = value(
  args,
  "--issue-repository",
  process.env.ISSUE_REPOSITORY ?? "bacluc-agent/agent-todo",
)!;
const repeat = args.includes("--repeat");
const options: LoopOptions = {
  repository,
  issueRepository,
  token: process.env.BACLUC_AGENT_GITHUB_TOKEN ?? process.env.GITHUB_TOKEN,
  model: value(args, "--model", process.env.MODEL),
  phases: parsePhases(value(args, "--phases")),
  cycles: repeat ? 0 : Number(value(args, "--cycles", "1")),
  pollSeconds: Number(value(args, "--poll", "0")),
  dryRun: args.includes("--dry-run"),
  launcher: args.includes("--dry-run")
    ? (process.env.AGENT_LOOPS_LAUNCHER ?? "start-ai-agent-devcontainer")
    : resolveLauncher(
        process.env.AGENT_LOOPS_LAUNCHER ?? "start-ai-agent-devcontainer",
        process.env.AGENT_LOOPS_LAUNCHER !== undefined,
      ),
  agentCommand:
    process.env.AGENT_LOOPS_AGENT_COMMAND ??
    'opencode run --agent {agent} --model ${MODEL:-opencode/big-pickle} "$(cat {prompt})"',
};

if (!options.dryRun && !options.token)
  throw new Error("BACLUC_AGENT_GITHUB_TOKEN or GITHUB_TOKEN is required");
if (!Number.isInteger(options.cycles) || options.cycles < 0)
  throw new Error("--cycles must be a non-negative integer");
if (!Number.isInteger(options.pollSeconds) || options.pollSeconds < 0)
  throw new Error("--poll must be a non-negative integer");

await run(options);
