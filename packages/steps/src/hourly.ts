import { runModelAvailability } from "./model-availability.ts";
import type { StepContext } from "./types.ts";

export async function runHourly(ctx: StepContext): Promise<void> {
  await ctx.github
    .ensureLabel(ctx.issueRepository, "agent-running")
    .catch(() => undefined);
  await ctx.github
    .ensureLabel(ctx.issueRepository, "agent-attempted")
    .catch(() => undefined);
  const issues = await ctx.github.searchIssues(
    `repo:${ctx.issueRepository} is:open is:issue label:ready-for-implementation -label:agent-running sort:created-asc`,
  );
  if (!issues.length || ctx.dryRun) return;
  const model = await runModelAvailability(ctx);
  const selected = await ctx.runAgent(
    issues.map((issue) => `${issue.number}: ${issue.title}`).join("\n"),
    "issue-selector",
  );
  const match = selected.match(/^SELECTED_ISSUE:\s*(\d+)\s*$/m);
  const number = match ? Number(match[1]) : undefined;
  if (!number || !issues.some((issue) => issue.number === number))
    throw new Error("issue-selector returned no valid SELECTED_ISSUE");
  await ctx.github.editIssue(ctx.issueRepository, number, {
    addLabels: ["agent-running", "agent-attempted"],
  });
  try {
    await ctx.runAgent(
      `Implement issue #${number} in ${ctx.issueRepository}\nModel: ${model}`,
      "coordinator",
    );
  } finally {
    await ctx.github
      .editIssue(ctx.issueRepository, number, {
        removeLabels: ["agent-running"],
      })
      .catch(() => undefined);
  }
}
