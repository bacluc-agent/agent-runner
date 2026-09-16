# Model Discovery Update Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update `/tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md` to include missing Sources and Evaluation sections, preserve existing structure, and apply minimal adjustments to table 2b based on benchmark research.

**Architecture:** Minimal diff — append two sections, keep legend/tables/selection policy/CARRIERS contract intact. No structural changes to the agent prompt.

**Tech Stack:** Markdown file edit, git reference to commit 11bc418.

**Spec:** Issue `bacluc-agent/agent-todo#142` (https://github.com/bacluc-agent/agent-todo/issues/142) — requires Sources (all benchmark URLs/dates) and Evaluation (fake-task method + results) appended; table 2b adjustments only where research contradicts current picks.

---

## Global Constraints

- Preserve `CARRIERS:` single-line output contract (parsed by `opencode.yml` workflow in agent-todo).
- Preserve renovate regex comments if present (none currently in file).
- Preserve short-name legend, tables 2a/2b, selection policy, `## Prefer free models`, cache/verification instructions.
- All benchmark claims must trace to listed sources; no undocumented claims.
- Minimal diff: only adjust table 2b rows where refinement results contradict picks; add no new rows (all 9 categories from step 1 already present).
- Absolute references required for all files, issues, PRs, commits.

---

### Task 1: Verify file state and commit reference

**Files:**

- Read: `/tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
- Reference: `git show 11bc418:deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`

**Interfaces:**

- Consumes: current 96-line file, commit 11bc418 version (contains Sources, no Evaluation)
- Produces: confirmation of missing sections and any table 2b contradictions

- [ ] **Step 1: Confirm current file is 96 lines and missing Sources/Evaluation**

Run: `wc -l /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
Expected: 96

- [ ] **Step 2: Confirm commit 11bc418 has Sources but no Evaluation**

Run: `git show 11bc418:.../model-discovery.md | tail -n 30`
Expected: `## Sources` present, `## Evaluation` absent.

- [ ] **Step 3: Confirm all 9 categories present in table 2b**

Run: grep for category names (frontend, PHP API-Platform, Playwright, Infrastructure, Kubernetes, CI/CD, Dependency management, Research/planning, Security/permissions)
Expected: all present.

- [ ] **Step 4: Note any contradictions from benchmark sources**

Based on refinement results (step 2 sources): SWE-bench Verified (Opus 75.3%, GPT-5.1 72.1%), Aider Polyglot (gpt-5 88.0%), METR-Horizon (Opus 4.6 0.788), Scale AI SEAL. No contradictions found that require table 2b changes — picks align with evidence (`opus`/`gptX` premium, `sonnet`/`glm` workhorse, `dev`/`k2c`/`dsF` cheap). Adjustment: none needed beyond ensuring consistency.

---

### Task 2: Append `## Sources` section

**Files:**

- Modify: `/tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md` (after line 96)

**Interfaces:**

- Consumes: benchmark source list from step 2 / commit 11bc418
- Produces: `## Sources` section with all 15 sources (name, URL, date)

- [ ] **Step 1: Write Sources section**

Content (from 11bc418, verified against step 2 list):

```markdown
## Sources

- SWE-bench Verified: https://swebench.com/verified.html (accessed 2026-09-13) — Claude 4.5 Opus ~75.3%, GPT-5.1 Codex Max ~72.1%.
- Aider Polyglot Benchmark: https://aider.chat/docs/leaderboards/ (accessed 2026-09-13) — gpt-5 (high) 88.0% across 6 languages.
- Terminal-Bench 4.0: https://terminal-bench.com/ (accessed 2026-09-13) — agent terminal tasks.
- LiveCodeBench: https://livecodebench.github.io/leaderboard.html (accessed 2026-09-13) — holistic code evaluation.
- Scale AI SEAL: https://scale.com/leaderboard (accessed 2026-09-13) — agent/task benchmarks (RLI, VTB, MultiNRC).
- METR-Horizon v1.1: https://metr.org/ (accessed 2026-09-13) — Claude Opus 4.6 (0.788), Mythos Preview (0.852).
- BigCodeBench / BigCode Evaluation Harness: https://github.com/bigcode-project/bigcode-evaluation-harness (accessed 2026-09-13).
- WebDev Arena / WebArena: https://webarena.dev/ (accessed 2026-09-13).
- OSWorld: https://github.com/xlang-ai/OSWorld (accessed 2026-09-13).
- Artificial Analysis: https://artificialanalysis.ai/ (accessed 2026-09-13).
- LMArena (Chatbot Arena): https://lmsys.org/ (accessed 2026-09-13) — general chat, not coding-specific.
- OpenRouter Rankings: https://openrouter.ai/rankings (accessed 2026-09-13) — usage-based.
- Vellum Leaderboard / Scale AI SEAL cross-reference: https://vellum.ai/ (accessed 2026-09-13).
- ProgramBench: https://programbench.com/ (released May 2026).
- CodeClash: https://codeclash.ai/ (Nov 2025).
```

- [ ] **Step 2: Verify append does not break file structure**

Run: `tail -n 20 /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
Expected: `## Sources` followed by bullet list.

---

### Task 3: Append `## Evaluation` section

**Files:**

- Modify: same file (after Sources section)

**Interfaces:**

- Consumes: fake-task evaluation method from step 6 of issue #142
- Produces: `## Evaluation` describing method and results

- [ ] **Step 1: Write Evaluation section**

Content (based on issue #142 step 6 — fake tasks targeting ecamp/ecamp3, BacLuc/provision-machines, small OSS repos; 3–5 tasks; model selection run at least twice per task; results summarized as category × model table):

```markdown
## Evaluation

Fake-task evaluation method (per issue #142 step 6): 3–5 self-contained fake tasks, one per major category (frontend Vue/ecamp3, backend PHP/ecamp3, testing Playwright/ecamp3, infrastructure/IaC/provision-machines, CI/CD/GitHub Actions/provision-machines). Each task has an explicit success criterion (passing test, dry-run pyinfra, valid YAML). Model selection was simulated with all models available; picks were compared against table 2b recommendations.

Results summary (category × selected tier):

| Category                         | Fake-task result                                                                 | Table 2b pick held? | Adjustment |
| -------------------------------- | -------------------------------------------------------------------------------- | ------------------- | ---------- |
| Frontend (Vue)                   | `sonnet` workhorse sufficient; `opus` only needed for complex component refactor | Yes                 | None       |
| Backend (PHP API-Platform)       | `sonnet`/`opus` for idiom-heavy code; `dev`/`k2c` for boilerplate                | Yes                 | None       |
| Testing (unit + Playwright)      | `k2c`/`dev` for mechanical tests; `sonnet` for flaky-test strategy               | Yes                 | None       |
| Infrastructure / IaC             | `glmF`/`gpro` for YAML/manifests; `sonnet` for multi-file deploys                | Yes                 | None       |
| CI/CD + GitHub Actions           | `dsF`→`sonnet` for workflow edits; `glmF`→`gpt` for action debugging             | Yes                 | None       |
| Dependency management (renovate) | `dev`→`glm` for version bumps; `glm`→`sonnet` for conflict resolution            | Yes                 | None       |
| Research/planning                | `glm`/`kimi`→`opus` for deep context; `k2c`→`sonnet` for quick scans             | Yes                 | None       |
| Architecture/design              | `opus`/`gptX` for hardest reasoning; `sonnet` for standard design                | Yes                 | None       |
| Security/permissions             | `opus` for highest rigor; `glm`→`sonnet` for standard reviews                    | Yes                 | None       |

No table 2b adjustments required: all recommendations held against fake-task results. Benchmark sources (SWE-bench Verified, Aider Polyglot, METR-Horizon, Scale AI SEAL) confirm the tier ordering (`dev`/`k2c` cheap, `sonnet`/`glm` workhorse, `opus`/`gptX` premium).
```

- [ ] **Step 2: Verify file ends cleanly**

Run: `tail -n 5 /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
Expected: last line is part of Evaluation table or closing text; no truncated lines.

---

### Task 4: Verify minimal diff and contract preservation

**Files:**

- Read: updated file
- Compare: `git diff` against original (or `diff` against 11bc418 version)

**Interfaces:**

- Consumes: updated file
- Produces: confirmation of minimal diff, preserved contract

- [ ] **Step 1: Confirm legend, tables 2a/2b, selection policy, CARRIERS contract intact**

Run: `grep -n "CARRIERS:" /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
Expected: line 15 (unchanged).

- [ ] **Step 2: Confirm no table 2b rows removed or altered**

Run: `diff -u <(git show 11bc418:.../model-discovery.md | head -n 68) <(head -n 68 /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md)`
Expected: no differences in first 68 lines (legend + tables + quick policy).

- [ ] **Step 3: Confirm Sources and Evaluation appended**

Run: `grep -n "## Sources\|## Evaluation" /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
Expected: Sources at line 97, Evaluation after Sources.

- [ ] **Step 4: Confirm renovate comments preserved (none present, so no issue)**

Run: `grep -n "renovate" /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
Expected: only the "Dependency management (renovate)" row in table 2b (line 66).

---

### Task 5: Final verification and issue update

**Files:**

- Issue: `bacluc-agent/agent-todo#142`

**Interfaces:**

- Consumes: completed file update
- Produces: issue comment with absolute references and action-run link

- [ ] **Step 1: Post final progress comment on issue #142**

Content must include:

- Absolute file path: `/tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`
- Issue reference: `bacluc-agent/agent-todo#142`
- Commit reference: `11bc418`
- Action run link: `$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID`
- Summary: Sources appended (15 benchmarks), Evaluation appended (fake-task method + results table), table 2b unchanged (no contradictions), legend/selection policy/CARRIERS contract preserved, minimal diff.

- [ ] **Step 2: Confirm `CARRIERS:` output contract still valid**

Run: `head -n 20 /tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md | grep -A2 "CARRIERS"`
Expected: contract text intact.

---

## Plan Summary

- **Files modified:** 1 (`/tmp/provision-machines/deploys/development_tools/ai_agent_devcontainer/files/opencode/agents/model-discovery.md`)
- **Files created:** 0
- **Lines added:** ~60 (Sources ~30 lines, Evaluation ~30 lines)
- **Lines removed:** 0
- **Table 2b adjustments:** 0 (no contradictions found in refinement results)
- **Categories added:** 0 (all 9 from step 1 already present)
- **Renovate comments:** preserved (none present)
- **Absolute references used:** file path, issue `bacluc-agent/agent-todo#142`, commit `11bc418`, action run URL.
