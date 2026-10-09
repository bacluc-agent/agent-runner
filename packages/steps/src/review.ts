import { runModelAvailability } from "./model-availability.ts";
import type { StepContext } from "./types.ts";

export async function runReview(ctx: StepContext): Promise<void> {
  await runModelAvailability(ctx);
  const reviewer = (await ctx.github.currentUser()).login;
  const processed = new Set<string>();
  for (;;) {
    const query = (author: string) =>
      `is:pr is:open author:${author} reviewed-by:BacLuc -label:agents-ignore`;
    const prs = [
      ...(await ctx.github.searchPullRequests(query(reviewer))),
      ...(await ctx.github.searchPullRequests(query("app/renovate"))),
    ].filter(
      (candidate, index, all) =>
        all.findIndex(
          (other) =>
            other.number === candidate.number &&
            other.repository === candidate.repository,
        ) === index,
    );
    const pr = prs.find(
      (candidate) =>
        !processed.has(
          `${candidate.repository ?? ctx.repository}#${candidate.number}`,
        ),
    );
    if (!pr) return;
    if (ctx.dryRun) return;
    processed.add(`${pr.repository ?? ctx.repository}#${pr.number}`);
    const current = await ctx.github.getPullRequest(
      pr.repository ?? ctx.repository,
      pr.number,
    );
    const comments = await ctx.github.listReviewComments(
      pr.repository ?? ctx.repository,
      pr.number,
    );
    await ctx.runAgent(
      `PR #${current.number}: ${current.title}\nBranch: ${current.head.ref}\nURL: ${current.html_url}\n\nReview comments:\n${comments.map((comment) => comment.body).join("\n")}`,
      "review",
    );
  }
}
