import type { StepContext } from "./types.ts";
import { spawnSync } from "node:child_process";

const preferred = [
  "opencode-go-openai/qwen3.8-flash",
  "opencode-go-openai-2/qwen3.8-flash",
  "opencode/big-pickle",
];
export function chooseModel(
  available: string[],
  denied: string[],
): string | undefined {
  return [
    ...preferred,
    ...available.filter((model) =>
      /^(opencode|openrouter)\/.*(?:-free|:free)$/.test(model),
    ),
  ].find(
    (model) =>
      available.includes(model) &&
      !denied.some((entry) => model.includes(entry)),
  );
}

export async function runModelAvailability(
  ctx: StepContext,
): Promise<string | undefined> {
  let available = (process.env.AVAILABLE_MODELS ?? "")
    .split(/\s+/)
    .filter(Boolean);
  if (!available.length && !ctx.dryRun) {
    const result = spawnSync(
      "python3",
      [
        process.env.AGENT_LOOPS_MODEL_AVAILABILITY ??
          ".github/actions/model-availability/model_availability.py",
      ],
      { encoding: "utf8" },
    );
    const marker = result.stdout?.split("Available models:\n")[1];
    available =
      marker
        ?.split("\n")
        .map((model) => model.trim())
        .filter(Boolean) ?? [];
  }
  const denied = (process.env.MODEL_DENY_LIST ?? "")
    .split(/\s+/)
    .filter(Boolean);
  const model = chooseModel(available, denied);
  if (!model && !ctx.dryRun) throw new Error("no available agent model");
  ctx.model = model;
  return model;
}
