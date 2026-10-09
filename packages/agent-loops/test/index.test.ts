import {
  GitHubClient,
  parsePhases,
  parseSelectedIssue,
  phaseOrder,
} from "../src/index.ts";
import assert from "node:assert/strict";
import test from "node:test";

test("phases always run in refine, hourly, review order", () => {
  assert.deepEqual(phaseOrder(["review", "refine"]), ["refine", "review"]);
});

test("phase parsing rejects unknown-only input", () => {
  assert.throws(() => parsePhases("unknown"), /--phases/);
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
