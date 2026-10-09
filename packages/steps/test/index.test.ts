import { runHourly } from "../src/hourly.ts";
import {
  chooseModel,
  runModelAvailability,
} from "../src/model-availability.ts";
import { validateRefinement } from "../src/refine.ts";
import { runRefine } from "../src/refine.ts";
import { runReview } from "../src/review.ts";
import assert from "node:assert/strict";
import test from "node:test";

test("refinement validation accepts exactly the required sections", () => {
  assert.equal(
    validateRefinement("## Goal\nDo it.\n\n## How to implement\n1. Do it."),
    undefined,
  );
  assert.equal(validateRefinement("bad"), "missing_goal_heading");
});

test("model selection honors preferred available models and deny list", () => {
  assert.equal(
    chooseModel(["opencode/weak-free", "opencode/big-pickle"], []),
    "opencode/big-pickle",
  );
  assert.equal(chooseModel(["opencode/big-pickle"], ["big-pickle"]), undefined);
  assert.equal(
    chooseModel(["opencode/other-model"], []),
    "opencode/other-model",
  );
});

test("model availability preserves an explicit model without probing", async () => {
  const ctx = {
    model: "provider/explicit",
    dryRun: true,
  } as never;
  assert.equal(await runModelAvailability(ctx), "provider/explicit");
  assert.equal(ctx.model, "provider/explicit");
});

test("model availability applies the repository deny list", async () => {
  const previousModels = process.env.AVAILABLE_MODELS;
  process.env.AVAILABLE_MODELS =
    "opencode/nemotron-3-ultra-free opencode/big-pickle";
  try {
    const ctx = { dryRun: true } as never;
    assert.equal(await runModelAvailability(ctx), "opencode/big-pickle");
  } finally {
    if (previousModels === undefined) delete process.env.AVAILABLE_MODELS;
    else process.env.AVAILABLE_MODELS = previousModels;
  }
});

test("model availability finds the default deny list outside the checkout", async () => {
  const previousModels = process.env.AVAILABLE_MODELS;
  const previousDenyList = process.env.MODEL_DENY_LIST_FILE;
  const previousCwd = process.cwd();
  process.env.AVAILABLE_MODELS =
    "opencode/nemotron-3-ultra-free opencode/big-pickle";
  delete process.env.MODEL_DENY_LIST_FILE;
  process.chdir("/tmp");
  try {
    const ctx = { dryRun: true } as never;
    assert.equal(await runModelAvailability(ctx), "opencode/big-pickle");
  } finally {
    process.chdir(previousCwd);
    if (previousModels === undefined) delete process.env.AVAILABLE_MODELS;
    else process.env.AVAILABLE_MODELS = previousModels;
    if (previousDenyList === undefined) delete process.env.MODEL_DENY_LIST_FILE;
    else process.env.MODEL_DENY_LIST_FILE = previousDenyList;
  }
});

test("refine dry-run is read-only while selecting a model", async () => {
  const previousModels = process.env.AVAILABLE_MODELS;
  process.env.AVAILABLE_MODELS = "opencode/big-pickle";
  let ensured = false;
  try {
    await runRefine({
      issueRepository: "owner/issues",
      dryRun: true,
      github: {
        ensureLabel: async () => {
          ensured = true;
          throw new Error("must not mutate");
        },
        searchIssues: async () => [],
      },
    } as never);
    assert.equal(ensured, false);
  } finally {
    if (previousModels === undefined) delete process.env.AVAILABLE_MODELS;
    else process.env.AVAILABLE_MODELS = previousModels;
  }
});

test("refine retries invalid output and preserves labels", async () => {
  const previousModels = process.env.AVAILABLE_MODELS;
  process.env.AVAILABLE_MODELS = "opencode/big-pickle";
  let attempts = 0;
  const edits: unknown[] = [];
  const ctx = {
    repository: "owner/repo",
    issueRepository: "owner/issues",
    token: "token",
    launcher: "launcher",
    agentCommand: "command",
    dryRun: false,
    github: {
      ensureLabel: async () => undefined,
      searchIssues: async () => [
        { number: 1, title: "title", body: "body", labels: [] },
      ],
      getIssue: async () => ({
        number: 1,
        title: "title",
        body: "body",
        labels: [{ name: "ready" }],
      }),
      editIssue: async (...args: unknown[]) => edits.push(args),
    },
    runAgent: async () =>
      ++attempts === 1 ? "bad" : "## Goal\nDone\n\n## How to implement\nDo it",
  } as never;
  try {
    await runRefine(ctx);
    assert.equal(attempts, 2);
    assert.deepEqual((edits[0] as unknown[])[2], {
      expectedBody: "body",
      body: "## Goal\nDone\n\n## How to implement\nDo it",
      addLabels: ["agent-refined"],
    });
  } finally {
    if (previousModels === undefined) delete process.env.AVAILABLE_MODELS;
    else process.env.AVAILABLE_MODELS = previousModels;
  }
});

test("hourly releases the claim when the coordinator fails", async () => {
  const previousModels = process.env.AVAILABLE_MODELS;
  process.env.AVAILABLE_MODELS = "opencode/big-pickle";
  const labels: unknown[] = [];
  const ctx = {
    repository: "owner/repo",
    issueRepository: "owner/issues",
    token: "token",
    launcher: "launcher",
    agentCommand: "command",
    dryRun: false,
    github: {
      ensureLabel: async () => undefined,
      searchIssues: async () => [
        { number: 2, title: "title", body: "body", labels: [] },
      ],
      editIssue: async (_repo: string, _number: number, options: unknown) =>
        labels.push(options),
    },
    runAgent: async (_prompt: string, agent: string) =>
      agent === "issue-selector"
        ? "SELECTED_ISSUE: 2"
        : Promise.reject(new Error("failed")),
  } as never;
  try {
    await assert.rejects(runHourly(ctx), /failed/);
    assert.deepEqual(labels, [
      { addLabels: ["agent-running", "agent-attempted"] },
      { removeLabels: ["agent-running"] },
    ]);
  } finally {
    if (previousModels === undefined) delete process.env.AVAILABLE_MODELS;
    else process.env.AVAILABLE_MODELS = previousModels;
  }
});

test("review rereads the PR and includes its current branch", async () => {
  const previousModels = process.env.AVAILABLE_MODELS;
  process.env.AVAILABLE_MODELS = "opencode/big-pickle";
  const prompts: string[] = [];
  let searches = 0;
  const ctx = {
    repository: "owner/repo",
    issueRepository: "owner/issues",
    token: "token",
    launcher: "launcher",
    agentCommand: "command",
    dryRun: false,
    github: {
      searchPullRequests: async () =>
        ++searches === 1
          ? [
              {
                number: 3,
                title: "PR",
                body: "",
                labels: [],
                repository: "owner/repo",
                html_url: "url",
              },
            ]
          : [],
      getPullRequest: async () => ({
        number: 3,
        title: "PR",
        body: "",
        labels: [],
        repository: "owner/repo",
        html_url: "url",
        head: { ref: "feature" },
      }),
      currentUser: async () => ({ login: "BacLuc" }),
      listReviewComments: async () => [{ id: 1, body: "fix" }],
    },
    runAgent: async (prompt: string) => {
      prompts.push(prompt);
      return "";
    },
  } as never;
  try {
    await runReview(ctx);
    assert.match(prompts[0], /Branch: feature/);
    assert.equal(searches, 4);
  } finally {
    if (previousModels === undefined) delete process.env.AVAILABLE_MODELS;
    else process.env.AVAILABLE_MODELS = previousModels;
  }
});
