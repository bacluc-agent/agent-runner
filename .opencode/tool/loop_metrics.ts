import { tool } from "@opencode-ai/plugin";
import { writeFileSync, appendFileSync } from "node:fs";

export interface LoopMetrics {
  steps: number;
  tokenCostPerStep: number;
  convergenceRate: number;
  failureMode: "success" | "max-steps" | "error" | "timeout" | "unknown";
  terminatedAt: string;
}

export function computeMetrics(
  steps: number,
  progressDelta: number,
  failureMode: LoopMetrics["failureMode"] = "unknown",
  tokenEstimate?: number,
): LoopMetrics {
  // ponytail: token cost estimated from model-discovery output or plumbed from context; upgrade when real token usage API available
  const tokenCostPerStep = tokenEstimate ?? Math.max(0.001, steps * 0.0005);
  const convergenceRate = progressDelta > 0 ? steps / progressDelta : steps;
  return {
    steps,
    tokenCostPerStep,
    convergenceRate,
    failureMode,
    terminatedAt: new Date().toISOString(),
  };
}

export function emitMetrics(
  metrics: LoopMetrics,
  summaryPath?: string,
  artifactPath?: string,
): { summary: string; artifact: string } {
  const summaryFile =
    summaryPath ?? process.env.GITHUB_STEP_SUMMARY ?? "/tmp/loop-summary.md";
  const artifactFile = artifactPath ?? "loop-metrics.json";

  const table = [
    "| Metric | Value |",
    "|---|---|",
    `| Steps | ${metrics.steps} |`,
    `| Token cost / step | ${metrics.tokenCostPerStep.toFixed(4)} |`,
    `| Convergence rate | ${metrics.convergenceRate.toFixed(4)} |`,
    `| Failure mode | ${metrics.failureMode} |`,
    `| Terminated at | ${metrics.terminatedAt} |`,
  ].join("\n");

  appendFileSync(summaryFile, "\n" + table + "\n");
  writeFileSync(artifactFile, JSON.stringify(metrics, null, 2) + "\n");

  return { summary: table, artifact: artifactFile };
}

export default tool({
  description:
    "Emit loop-termination metrics (step count, token cost, convergence rate, failure mode) to GITHUB_STEP_SUMMARY and loop-metrics.json artifact.",
  args: {
    steps: tool.schema.number().int().min(0).describe("Loop step count"),
    progressDelta: tool.schema
      .number()
      .min(0)
      .describe("Progress delta for convergence rate"),
    failureMode: tool.schema
      .string()
      .optional()
      .describe("Failure mode: success, max-steps, error, timeout, unknown"),
    tokenEstimate: tool.schema
      .number()
      .optional()
      .describe("Estimated token cost per step"),
  },
  async execute(args, context) {
    const mode = (args.failureMode as LoopMetrics["failureMode"]) ?? "unknown";
    const metrics = computeMetrics(
      args.steps,
      args.progressDelta ?? 1,
      mode,
      args.tokenEstimate,
    );
    const result = emitMetrics(metrics);
    return `Metrics emitted: ${JSON.stringify(metrics)}\nSummary: ${result.summary}\nArtifact: ${result.artifact}`;
  },
});
