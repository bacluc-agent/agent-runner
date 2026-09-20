import test from "node:test";
import assert from "node:assert/strict";
import { terminateLoop } from "./loop_termination_guard.ts";

test("terminateLoop emits metrics through shared guard", () => {
  const summary = terminateLoop(7, 2, "success", 0.02);
  assert.ok(typeof summary === "string");
  assert.ok(summary.includes("success"));
  assert.ok(summary.includes("7"));
});
