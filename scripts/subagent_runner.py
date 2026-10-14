#!/usr/bin/env python3
"""Run independently modeled agents concurrently from a JSON configuration."""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys


def command(backend, model, prompt, name="coordinator", title=None):
    if backend == "opencode":
        return [
            "opencode", "run", "--agent", name, "--model", model,
            *( ["--title", title] if title else [] ), prompt,
        ]
    if backend == "t3-code":
        return ["t3-code", "run", "--model", model, "--prompt", prompt]
    raise ValueError(f"unsupported backend: {backend}")


def t3_code_executable():
    executable = next(
        (path for name in ("t3-code", "t3") if (path := shutil.which(name))), None
    )
    if not executable:
        raise RuntimeError(
            "T3 Code headless agent execution is experimental and unsupported: no `t3-code` or `t3` CLI is on PATH. "
            "The official CLI provides server commands such as `t3 serve`, not the required `run` command; use OpenCode."
        )
    try:
        help_result = subprocess.run(
            [executable, "run", "--help"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(
            f"T3 Code headless agent execution is unsupported: `{executable} run --help` could not be verified; "
            "expected a `run` command with `--model` and `--prompt`. Use OpenCode."
        ) from error
    help_text = help_result.stdout or ""
    if help_result.returncode or not all(
        re.search(rf"(?<![\w-]){flag}(?![\w-])", help_text)
        for flag in ("--model", "--prompt")
    ):
        raise RuntimeError(
            f"T3 Code headless agent execution is unsupported: `{executable} run --help` did not verify a `run` "
            "command with `--model` and `--prompt`. The official CLI documents `t3 serve` for headless server use, "
            "not one-shot agent execution; use OpenCode."
        )
    return executable


def run_agent(agent, backend):
    args = command(
        backend, agent["model"], agent["prompt"],
        agent.get("name", "coordinator"), agent.get("title"),
    )
    executable = args[0]
    if backend == "t3-code":
        args[0] = t3_code_executable()
    elif not shutil.which(executable):
        raise RuntimeError(f"{executable} CLI not found")
    env = os.environ.copy()
    if agent.get("config"):
        if backend == "opencode":
            env["OPENCODE_CONFIG"] = agent["config"]
    return subprocess.run(
        args,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        env=env,
    ).stdout


def dispatch(agents, backend):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(agents) or 1) as pool:
        futures = [pool.submit(run_agent, agent, backend) for agent in agents]
        return [future.result() for future in futures]


def execute(config):
    backend = config["backend"]
    try:
        results = dispatch(config["agents"], backend)
    except (subprocess.CalledProcessError, RuntimeError):
        if "fallback" not in config:
            raise
        return [run_agent(config["fallback"], backend)]
    if config.get("judge"):
        judge = dict(config["judge"])
        judge["prompt"] = judge["prompt"].format(outputs="\n\n".join(results))
        try:
            run_agent(judge, backend)
        except (subprocess.CalledProcessError, RuntimeError) as error:
            print(f"subagent runner: optional judge failed: {error}", file=sys.stderr)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        with open(args.config, encoding="utf-8") as config_file:
            output = execute(json.load(config_file))
        print("\n".join(output))
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"subagent runner: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
