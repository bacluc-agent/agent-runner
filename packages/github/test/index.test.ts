import { GitHubClient } from "../src/index.ts";
import assert from "node:assert/strict";
import test from "node:test";

test("GitHub client sends authenticated typed requests", async () => {
  const requests: Array<{ url: string; init: RequestInit }> = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input, init = {}) => {
    requests.push({ url: String(input), init });
    return new Response(JSON.stringify({ items: [{ number: 3 }] }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };
  try {
    const client = new GitHubClient("secret", "https://example.test");
    assert.deepEqual(await client.searchIssues("repo:owner/repo"), [
      { number: 3 },
    ]);
    assert.equal(
      requests[0].url,
      "https://example.test/search/issues?q=repo%3Aowner%2Frepo&per_page=100&page=1",
    );
    assert.equal(
      (requests[0].init.headers as Record<string, string>).Authorization,
      "Bearer secret",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("comment upsert edits the existing marker comment", async () => {
  const bodies: string[] = [];
  const originalFetch = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async (_input, init = {}) => {
    if (init.body) bodies.push(String(init.body));
    calls += 1;
    return new Response(
      calls === 1
        ? JSON.stringify([{ id: 9, body: "<!-- agent-progress --> old" }])
        : JSON.stringify({ id: 9, body: "new" }),
      { status: 200 },
    );
  };
  try {
    const client = new GitHubClient("secret", "https://example.test");
    await client.upsertComment("owner/repo", 1, "new");
    assert.equal(bodies.length, 1);
    assert.deepEqual(JSON.parse(bodies[0]), { body: "new" });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("list issue comments follow Link pagination", async () => {
  const urls: string[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input) => {
    urls.push(String(input));
    return new Response(
      JSON.stringify(
        urls.length === 1
          ? [{ id: 1, body: "first" }]
          : [{ id: 2, body: "second" }],
      ),
      {
        status: 200,
        headers:
          urls.length === 1
            ? {
                link: '<https://example.test/repos/o/r/issues/7/comments?per_page=100&page=2>; rel="next"',
              }
            : {},
      },
    );
  };
  try {
    const client = new GitHubClient("token", "https://example.test");
    assert.deepEqual(await client.listIssueComments("o/r", 7), [
      { id: 1, body: "first" },
      { id: 2, body: "second" },
    ]);
    assert.equal(
      urls[0],
      "https://example.test/repos/o/r/issues/7/comments?per_page=100&page=1",
    );
    assert.equal(
      urls[1],
      "https://example.test/repos/o/r/issues/7/comments?per_page=100&page=2",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("list review comments follow Link pagination", async () => {
  const urls: string[] = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input) => {
    urls.push(String(input));
    return new Response(
      JSON.stringify(
        urls.length === 1
          ? [{ id: 1, body: "first" }]
          : [{ id: 2, body: "second" }],
      ),
      {
        status: 200,
        headers:
          urls.length === 1
            ? {
                link: '<https://example.test/repos/o/r/pulls/7/comments?per_page=100&page=2>; rel="next"',
              }
            : {},
      },
    );
  };
  try {
    const client = new GitHubClient("token", "https://example.test");
    assert.deepEqual(await client.listReviewComments("o/r", 7), [
      { id: 1, body: "first" },
      { id: 2, body: "second" },
    ]);
    assert.equal(
      urls[0],
      "https://example.test/repos/o/r/pulls/7/comments?per_page=100&page=1",
    );
    assert.equal(
      urls[1],
      "https://example.test/repos/o/r/pulls/7/comments?per_page=100&page=2",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
