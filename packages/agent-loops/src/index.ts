import { spawn } from "node:child_process";
import { chmod, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

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

export type Issue = { number: number; title: string; body: string };
export type PullRequest = {
  number: number;
  title: string;
  url: string;
  repository: string;
};

export class GitHubClient {
  private readonly token: string;
  private readonly apiBase: string;

  constructor(token: string, apiBase = "https://api.github.com") {
    this.token = token;
    this.apiBase = apiBase;
  }

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.apiBase}/${path.replace(/^\//, "")}`, {
      ...init,
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${this.token}`,
        "X-GitHub-Api-Version": "2022-11-28",
        ...(init.headers ?? {}),
      },
    });
    const body = await response.text();
    if (!response.ok) throw new Error(`GitHub ${response.status}: ${body}`);
    return body ? (JSON.parse(body) as T) : (undefined as T);
  }

  async issues(query: string): Promise<Issue[]> {
    const result = await this.request<{ items: Issue[] }>(
      `search/issues?q=${encodeURIComponent(query)}&per_page=50`,
    );
    return result.items;
  }

  async issue(repository: string, number: number): Promise<Issue> {
    return this.request<Issue>(`repos/${repository}/issues/${number}`);
  }

  async editIssue(
    repository: string,
    number: number,
    body: string,
    labels: string[],
  ): Promise<void> {
    await this.request(`repos/${repository}/issues/${number}`, {
      method: "PATCH",
      body: JSON.stringify({ body, labels }),
      headers: { "Content-Type": "application/json" },
    });
  }

  async pullRequests(query: string): Promise<PullRequest[]> {
    const result = await this.request<{
      items: Array<{
        number: number;
        title: string;
        html_url: string;
        repository_url: string;
      }>;
    }>(`search/issues?q=${encodeURIComponent(query)}&per_page=50`);
    return result.items.map((item) => ({
      number: item.number,
      title: item.title,
      url: item.html_url,
      repository: item.repository_url.replace(
        "https://api.github.com/repos/",
        "",
      ),
    }));
  }
}

export function phaseOrder(phases: Phase[]): Phase[] {
  const order: Phase[] = ["refine", "hourly", "review"];
  return order.filter((phase) => phases.includes(phase));
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

async function command(
  command: string,
  cwd: string,
  env: NodeJS.ProcessEnv,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("sh", ["-c", command], {
      cwd,
      env,
      stdio: ["ignore", "pipe", "inherit"],
    });
    let output = "";
    child.stdout.on("data", (chunk) => (output += chunk));
    child.on("error", reject);
    child.on("close", (status) =>
      status === 0
        ? resolve(output)
        : reject(new Error(`agent exited with ${status}`)),
    );
  });
}

async function runAgent(
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
    `#!/bin/sh\nprintf '%s\\n' "$AGENT_LOOPS_GIT_TOKEN"\n`,
    "utf8",
  );
  await chmod(askpass, 0o700);
  const env = {
    ...process.env,
    AGENT_LOOPS_AGENT: agent,
    AGENT_LOOPS_GIT_TOKEN: options.token ?? "",
    MODEL: options.model ?? process.env.MODEL ?? "opencode/big-pickle",
    GIT_ASKPASS: askpass,
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
    const containerPromptFile = `/workspaces/${workspace.split("/").pop()}/prompt.txt`;
    env.AGENT_LOOPS_PROMPT_FILE = containerPromptFile;
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
  github: GitHubClient,
): Promise<void> {
  for (const phase of phaseOrder(options.phases)) {
    if (phase === "refine") {
      const issues = await github.issues(
        `repo:${options.issueRepository} is:open is:issue -label:agent-refined -label:ready-for-implementation -label:agent-ignore sort:created-asc`,
      );
      for (const candidate of issues) {
        if (options.dryRun) {
          console.log(`dry-run refine #${candidate.number}`);
          continue;
        }
        const issue = await github.issue(
          options.issueRepository,
          candidate.number,
        );
        const output = await runAgent(
          options,
          `Refine issue #${issue.number}\n\n${issue.title}\n\n${issue.body}`,
          "issue-refiner",
        );
        await github.editIssue(
          options.issueRepository,
          issue.number,
          output.trim(),
          ["agent-refined"],
        );
      }
    }
    if (phase === "hourly") {
      const issues = await github.issues(
        `repo:${options.issueRepository} is:open is:issue label:ready-for-implementation -label:agent-running sort:created-asc`,
      );
      if (!issues.length) continue;
      const candidates = issues.map((issue) => issue.number);
      if (options.dryRun) {
        console.log(`dry-run hourly #${candidates[0]}`);
        continue;
      }
      const selected = parseSelectedIssue(
        await runAgent(
          options,
          issues.map((issue) => `${issue.number}: ${issue.title}`).join("\n"),
          "issue-selector",
        ),
        candidates,
      );
      if (selected === undefined)
        throw new Error("issue-selector returned no valid SELECTED_ISSUE");
      await runAgent(
        options,
        `Implement issue #${selected} in ${options.issueRepository}`,
        "coordinator",
      );
    }
    if (phase === "review") {
      const prs = await github.pullRequests(
        `is:pr is:open reviewed-by:BacLuc -label:agents-ignore`,
      );
      for (const pr of prs) {
        if (options.dryRun) {
          console.log(`dry-run review ${pr.url}`);
          continue;
        }
        await runAgent(
          options,
          `Apply review comments for ${pr.url}\n${pr.title}`,
          "review",
        );
      }
    }
  }
}

export async function run(options: LoopOptions): Promise<void> {
  const github = new GitHubClient(
    options.token ??
      process.env.BACLUC_AGENT_GITHUB_TOKEN ??
      process.env.GITHUB_TOKEN ??
      "",
  );
  for (
    let cycle = 0;
    options.cycles === 0 || cycle < options.cycles;
    cycle += 1
  ) {
    await runCycle(options, github);
    if (
      options.pollSeconds > 0 &&
      (options.cycles === 0 || cycle + 1 < options.cycles)
    )
      await new Promise((resolve) =>
        setTimeout(resolve, options.pollSeconds * 1000),
      );
  }
}
