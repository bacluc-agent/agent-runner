import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { terminateLoop } from "./loop_termination_guard.ts";

test("terminateLoop emits metrics through shared guard", () => {
  const worktree = mkdtempSync(join(tmpdir(), "loop-termination-"));
  const summaryPath = join(worktree, "summary.md");
  const artifactPath = join(worktree, "metrics.json");
  const summary = terminateLoop(
    7,
    2,
    "success",
    0.02,
    summaryPath,
    artifactPath,
  );
  assert.ok(typeof summary === "string");
  assert.ok(summary.includes("success"));
  assert.ok(summary.includes("7"));
  assert.ok(readFileSync(summaryPath, "utf8").includes("success"));
  assert.equal(JSON.parse(readFileSync(artifactPath, "utf8")).steps, 7);
  rmSync(worktree, { recursive: true, force: true });
});
