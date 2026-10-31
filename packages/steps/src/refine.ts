import { runModelAvailability } from "./model-availability.ts";
import type { StepContext } from "./types.ts";

export function validateRefinement(output: string): string | undefined {
  const text = output.trim();
  if (!text) return "empty";
  if (text.startsWith("```") || text.length > 4000)
    return text.startsWith("```") ? "fenced_output" : "too_long";
  if (!/^## Goal\s*$/m.test(text)) return "missing_goal_heading";
  if (!/^## How to implement\s*$/m.test(text)) return "missing_impl_heading";
  if (!/^## Goal\s*\n+[\s\S]+?\n+## How to implement\s*\n+[\s\S]+$/m.test(text))
    return "wrong_order";
  if (/^## (?!Goal$|How to implement$).+/m.test(text)) return "extra_sections";
  if (/ignore previous instructions|system prompt/i.test(text))
    return "hostile_text";
  return undefined;
}

export async function runRefine(ctx: StepContext): Promise<void> {
  await runModelAvailability(ctx);
  if (!ctx.dryRun)
    await ctx.github
      .ensureLabel(ctx.issueRepository, "agent-refined")
      .catch(() => undefined);
  const issues = await ctx.github.searchIssues(
    `repo:${ctx.issueRepository} is:open is:issue -label:agent-refined -label:ready-for-implementation -label:agent-ignore sort:created-asc`,
  );
  for (const candidate of issues) {
    if (ctx.dryRun) continue;
    const issue = await ctx.github.getIssue(
      ctx.issueRepository,
      candidate.number,
    );
    let reason = "";
    for (let attempt = 0; attempt < 2; attempt += 1) {
      const output = await ctx.runAgent(
        `Refine issue #${issue.number}\n\n${issue.title}\n\n${issue.body}\n${reason}`,
        "issue-refiner",
      );
      reason = validateRefinement(output) ?? "";
      if (!reason) {
        await ctx.github.editIssue(ctx.issueRepository, issue.number, {
          expectedBody: issue.body,
          body: output.trim(),
          addLabels: ["agent-refined"],
        });
        break;
      }
      if (attempt === 1)
        throw new Error(
          `issue #${issue.number} refinement rejected: ${reason}`,
        );
    }
  }
}
