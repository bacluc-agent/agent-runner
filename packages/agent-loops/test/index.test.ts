import {
  GitHubClient,
  parsePhases,
  parseSelectedIssue,
  phaseOrder,
  refine,
  resolveLauncher,
  runCycle,
  type LoopOptions,
} from "../src/index.ts";
import assert from "node:assert/strict";
import { chmod, mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

test("phases always run in refine, hourly, review order", () => {
  assert.deepEqual(phaseOrder(["review", "refine"]), ["refine", "review"]);
});

test("phase parsing rejects unknown-only input", () => {
  assert.throws(() => parsePhases("unknown"), /--phases/);
});

test("launcher resolution accepts an executable absolute override", async () => {
  const directory = await mkdtemp(join(tmpdir(), "agent-loops-test-"));
  const launcher = join(directory, "launcher");
  await writeFile(launcher, "#!/bin/sh\n");
  await chmod(launcher, 0o755);
  try {
    assert.equal(resolveLauncher(launcher, true), launcher);
    assert.throws(
      () => resolveLauncher(join(directory, "missing"), true),
      /not executable/,
    );
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test("launcher resolution searches PATH before HOME/bin", async () => {
  const directory = await mkdtemp(join(tmpdir(), "agent-loops-test-"));
  const pathLauncher = join(directory, "start-ai-agent-devcontainer");
  const home = join(directory, "home");
  const homeLauncher = join(home, "bin", "start-ai-agent-devcontainer");
  await writeFile(pathLauncher, "#!/bin/sh\n");
  await chmod(pathLauncher, 0o755);
  await mkdir(join(home, "bin"), { recursive: true });
  await writeFile(homeLauncher, "#!/bin/sh\n");
  await chmod(homeLauncher, 0o755);
  const previousPath = process.env.PATH;
  const previousHome = process.env.HOME;
  process.env.PATH = directory;
  process.env.HOME = home;
  try {
    assert.equal(resolveLauncher(), pathLauncher);
    await rm(pathLauncher);
    assert.equal(resolveLauncher(), homeLauncher);
  } finally {
    if (previousPath === undefined) delete process.env.PATH;
    else process.env.PATH = previousPath;
    if (previousHome === undefined) delete process.env.HOME;
    else process.env.HOME = previousHome;
    await rm(directory, { recursive: true, force: true });
  }
});

test("each phase resolves availability independently", async () => {
  const previousModels = process.env.AVAILABLE_MODELS;
  const previousLog = console.log;
  process.env.AVAILABLE_MODELS = "opencode/first";
  const logs: string[] = [];
  let searches = 0;
  const options = {
    repository: "owner/repo",
    issueRepository: "owner/issues",
    phases: ["refine", "hourly"],
    cycles: 1,
    pollSeconds: 0,
    dryRun: true,
    launcher: "launcher",
    agentCommand: "command",
  } satisfies LoopOptions;
  const github = {
    searchIssues: async () => {
      if (++searches === 1) process.env.AVAILABLE_MODELS = "opencode/second";
      return [];
    },
    ensureLabel: async () => undefined,
  } as never;
  try {
    console.log = (message?: unknown) => logs.push(String(message));
    await runCycle(options, github);
    assert.equal(
      logs
        .filter((message) => message.startsWith("selected model="))
        .join("\n"),
      "selected model=opencode/first\nselected model=opencode/second",
    );
  } finally {
    console.log = previousLog;
    if (previousModels === undefined) delete process.env.AVAILABLE_MODELS;
    else process.env.AVAILABLE_MODELS = previousModels;
  }
});

test("selected issue must be one of the candidates", () => {
  assert.equal(parseSelectedIssue("SELECTED_ISSUE: 12", [12, 13]), 12);
  assert.equal(parseSelectedIssue("SELECTED_ISSUE: 99", [12, 13]), undefined);
});

test("issue edits preserve labels after a fresh body check", async () => {
  const requests: RequestInit[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (_input, init) => {
    requests.push(init ?? {});
    return new Response(
      requests.length === 1
        ? JSON.stringify({ body: "old", labels: [{ name: "ready" }] })
        : "",
      { status: 200 },
    );
  };
  try {
    await new GitHubClient("token", "https://example.test").editIssue(
      "owner/repo",
      12,
      "old",
      "new",
      "agent-refined",
    );
    assert.deepEqual(JSON.parse(String(requests[1].body)), {
      body: "new",
      labels: ["ready", "agent-refined"],
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("searches follow GitHub pagination", async () => {
  const urls: string[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input) => {
    urls.push(String(input));
    return new Response(
      JSON.stringify({
        items: urls.length === 1 ? [{ number: 1 }] : [{ number: 2 }],
      }),
      {
        status: 200,
        headers:
          urls.length === 1
            ? {
                link: '<https://example.test/search/issues?page=2>; rel="next"',
              }
            : {},
      },
    );
  };
  try {
    const client = new GitHubClient("token", "https://example.test");
    assert.deepEqual(await client.searchIssues("repo:owner/repo"), [
      { number: 1 },
      { number: 2 },
    ]);
    assert.match(urls[0], /per_page=100&page=1/);
    assert.equal(urls[1], "https://example.test/search/issues?page=2");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
