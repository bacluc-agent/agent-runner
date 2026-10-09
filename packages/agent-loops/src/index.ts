import { GitHubClient } from "@bacluc-agent/github";
import {
  runHourly,
  runRefine,
  runReview,
  type StepContext,
} from "@bacluc-agent/steps";
import { spawn } from "node:child_process";
import { chmod, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

export { GitHubClient } from "@bacluc-agent/github";
export type { Issue, PullRequest } from "@bacluc-agent/github";

export type Phase = "refine" | "hourly" | "review";
export type LoopOptions = {
  repository: string;
  issueRepository: string;
  token?: string;
  model?: string;
  phases: Phase[];
  cycles: number;
  pollSeconds: number;
  dryRun: boolean;
  launcher: string;
  agentCommand: string;
};

export function phaseOrder(phases: Phase[]): Phase[] {
  return (["refine", "hourly", "review"] as Phase[]).filter((phase) =>
    phases.includes(phase),
  );
}
export function parseSelectedIssue(
  output: string,
  candidates: number[],
): number | undefined {
  const match = output.match(/^SELECTED_ISSUE:\s*(\d+)\s*$/m);
  const number = match ? Number(match[1]) : undefined;
  return number !== undefined && candidates.includes(number)
    ? number
    : undefined;
}
export function parsePhases(value = "refine,hourly,review"): Phase[] {
  const phases = value
    .split(",")
    .filter((phase): phase is Phase =>
      ["refine", "hourly", "review"].includes(phase),
    );
  if (!phases.length)
    throw new Error("--phases must contain refine, hourly, or review");
  return phaseOrder(phases);
}

function context(options: LoopOptions, github: GitHubClient): StepContext {
  return {
    ...options,
    github,
    runAgent: (prompt, agent) => runAgent(options, prompt, agent),
  };
}

function command(
  commandLine: string,
  cwd: string,
  env: NodeJS.ProcessEnv,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("sh", ["-c", commandLine], {
      cwd,
      env,
      stdio: ["ignore", "pipe", "inherit"],
    });
    let output = "";
    const forwardSignal = (signal: NodeJS.Signals) => child.kill(signal);
    process.once("SIGINT", forwardSignal);
    process.once("SIGTERM", forwardSignal);
    child.stdout.on("data", (chunk) => (output += chunk));
    child.on("error", reject);
    child.on("close", (status, signal) => {
      process.off("SIGINT", forwardSignal);
      process.off("SIGTERM", forwardSignal);
      status === 0
        ? resolve(output)
        : reject(new Error(`agent exited with ${status ?? signal}`));
    });
  });
}

export async function runAgent(
  options: LoopOptions,
  prompt: string,
  agent: string,
): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "agent-loops-"));
  const workspace = join(root, "workspace");
  await mkdir(workspace);
  const askpass = join(root, ".git-askpass");
  await writeFile(
    askpass,
    "#!/bin/sh\nprintf '%s\\n' \"$AGENT_LOOPS_GIT_TOKEN\"\n",
    "utf8",
  );
  await chmod(askpass, 0o700);
  const env = {
    ...process.env,
    AGENT_LOOPS_AGENT: agent,
    AGENT_LOOPS_GIT_TOKEN: options.token ?? "",
    MODEL: options.model ?? process.env.MODEL ?? "opencode/big-pickle",
    GIT_ASKPASS: askpass,
    GIT_ASKPASS_SOURCE: askpass,
    GIT_ASKPASS_TARGET: "/tmp/agent-loops-git-askpass",
    GIT_TERMINAL_PROMPT: "0",
  };
  const commandLine = options.agentCommand
    .replaceAll("{agent}", agent)
    .replaceAll("{prompt}", "$AGENT_LOOPS_PROMPT_FILE");
  try {
    const repository =
      options.repository.includes("://") || options.repository.startsWith("/")
        ? options.repository
        : `https://github.com/${options.repository}.git`;
    await command(
      `git clone --depth 1 "$AGENT_LOOPS_REPOSITORY" "$PWD"`,
      workspace,
      { ...env, AGENT_LOOPS_REPOSITORY: repository },
    );
    const promptFile = join(workspace, "prompt.txt");
    await writeFile(promptFile, prompt, "utf8");
    env.AGENT_LOOPS_PROMPT_FILE = `/workspaces/${workspace.split("/").pop()}/prompt.txt`;
    await command(
      `${options.launcher} --workspace-dir "$PWD" --no-open`,
      workspace,
      env,
    );
    return await command(
      `devcontainer exec --workspace-folder "$PWD" sh -lc '${commandLine.replaceAll("'", "'\\''")}'`,
      workspace,
      env,
    );
  } finally {
    await command(
      `${options.launcher} --workspace-dir "$PWD" --down --no-open`,
      workspace,
      env,
    ).catch(() => undefined);
    await rm(root, { recursive: true, force: true });
  }
}

export async function runCycle(
  options: LoopOptions,
  github = new GitHubClient(
    options.token ??
      process.env.BACLUC_AGENT_GITHUB_TOKEN ??
      process.env.GITHUB_TOKEN ??
      "",
  ),
): Promise<void> {
  const ctx = context(options, github);
  for (const phase of phaseOrder(options.phases)) {
    if (phase === "refine") await runRefine(ctx);
    if (phase === "hourly") await runHourly(ctx);
    if (phase === "review") await runReview(ctx);
  }
}

export async function refine(
  options: LoopOptions,
  github = new GitHubClient(
    options.token ??
      process.env.BACLUC_AGENT_GITHUB_TOKEN ??
      process.env.GITHUB_TOKEN ??
      "",
  ),
): Promise<void> {
  await runRefine(context(options, github));
}

export async function issues(
  options: LoopOptions,
  github = new GitHubClient(
    options.token ??
      process.env.BACLUC_AGENT_GITHUB_TOKEN ??
      process.env.GITHUB_TOKEN ??
      "",
  ),
): Promise<void> {
  await runHourly(context(options, github));
}

export async function review(
  options: LoopOptions,
  github = new GitHubClient(
    options.token ??
      process.env.BACLUC_AGENT_GITHUB_TOKEN ??
      process.env.GITHUB_TOKEN ??
      "",
  ),
): Promise<void> {
  await runReview(context(options, github));
}

export async function run(options: LoopOptions): Promise<void> {
  for (
    let cycle = 0;
    options.cycles === 0 || cycle < options.cycles;
    cycle += 1
  ) {
    await runCycle(options);
    if (
      options.pollSeconds > 0 &&
      (options.cycles === 0 || cycle + 1 < options.cycles)
    )
      await new Promise((resolve) =>
        setTimeout(resolve, options.pollSeconds * 1000),
      );
  }
}
