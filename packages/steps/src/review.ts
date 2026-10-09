import type { StepContext } from "./types.ts";

export async function runReview(ctx: StepContext): Promise<void> {
  const processed = new Set<string>();
  for (;;) {
    const prs = await ctx.github.searchPullRequests(
      `is:pr is:open reviewed-by:BacLuc -label:agents-ignore`,
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
