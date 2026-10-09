import { parsePhases, parseSelectedIssue, phaseOrder } from "../src/index.ts";
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
