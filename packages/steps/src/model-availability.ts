import type { StepContext } from "./types.ts";
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

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
    ...available,
  ].find(
    (model) =>
      available.includes(model) &&
      !denied.some((entry) => new RegExp(entry).test(model)),
  );
}

function denyList(): string[] {
  const path = resolve(
    process.env.MODEL_DENY_LIST_FILE ?? "scripts/model-deny-list.txt",
  );
  return readFileSync(path, "utf8").split(/\r?\n/).filter(Boolean);
}

export async function runModelAvailability(
  ctx: StepContext,
): Promise<string | undefined> {
  if (ctx.requestedModel) {
    ctx.model = ctx.requestedModel;
    ctx.log?.(`selected model=${ctx.model}`);
    return ctx.model;
  }
  if (ctx.model) {
    ctx.log?.(`selected model=${ctx.model}`);
    return ctx.model;
  }
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
  const denied = denyList();
  const model =
    chooseModel(available, denied) ??
    (ctx.dryRun ? chooseModel(preferred, denied) : undefined);
  if (!model && !ctx.dryRun) throw new Error("no available agent model");
  ctx.model = model;
  ctx.log?.(`selected model=${model ?? "unavailable"}`);
  return model;
}
