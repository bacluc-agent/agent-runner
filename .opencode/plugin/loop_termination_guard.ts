import { computeMetrics, emitMetrics } from "../tool/loop_metrics.ts";

// ponytail: shared loop-termination guard; all agent-run callers route through this point. Upgrade when per-caller granular tracking needed.
export function terminateLoop(
  steps: number,
  progressDelta: number,
  failureMode:
    "success" | "max-steps" | "error" | "timeout" | "unknown" = "unknown",
  tokenEstimate?: number,
): string {
  const metrics = computeMetrics(
    steps,
    progressDelta,
    failureMode,
    tokenEstimate,
  );
  const result = emitMetrics(metrics);
  return result.summary;
}
