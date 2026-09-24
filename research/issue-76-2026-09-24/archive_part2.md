# Archive: issue #76 comments (2026-09-24) part 2/3

Source issue: https://github.com/bacluc-agent/agent-todo/issues/76
Archive date: 2026-09-24
Part: 2/3 — comments 6–11 of 20
Full archive: [part 1](https://github.com/bacluc-agent/agent-todo/issues/266) | [part 2](https://github.com/bacluc-agent/agent-todo/issues/267) | [part 3](https://github.com/bacluc-agent/agent-todo/issues/268)
Note: comments by @BacLuc (2) and the run-tracking comment (1) remain on the source issue.
Note: comment 20 (run-tracking) may have been updated after this snapshot.

---

**Archived comment 6/20** — @bacluc-agent — 2026-09-17T20:42:56Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5720958731)

## Research continuation: example code, search keywords, direct links, and proposed issues

Run: https://github.com/bacluc-agent/agent-runner/actions/runs/35271552395 — model: opencode/big-pickle

Read: AGENTS.md

This comment extends the earlier survey (2026-09-06/07) with the four pieces requested in the human comment of 2026-09-07: **example code**, **web search keywords**, **direct links**, and **proposed issues**. All URLs below were re-verified with HTTP 200 on 2026-09-17.

---

## 1. Link verification — all previously cited links are alive

All 27 URLs from the prior research comment were re-checked (`curl -L`, HTTP status) and are **alive (200)**. arXiv IDs were title-checked against the abstract pages — every ID maps to the correct paper. The four LangGraph notebooks were downloaded and parsed: they contain real code (reflection: 12 code cells, reflexion: 13, lats: 19, rewoo: 16).

One cosmetic fix: `lapisrocks/LanguageAgentTreeSearch` now redirects to **`andyz245/LanguageAgentTreeSearch`** (owner renamed; same repo, 859 stars). The canonical URL is https://github.com/andyz245/LanguageAgentTreeSearch.

One dead link found outside the list: the OpenAI cookbook example `cookbook.openai.com/examples/how_to_evaluate_and_refine_model_outputs` returns **404** (cookbook migrated to developers.openai.com and the example was removed). Do not cite it; the LangChain blog post below is the better replacement.

---

## 2. Example code — additional inspectable implementations

For each pattern, 1–2 additional real implementations beyond the prior list, with a note on how the loop is built (state, termination, memory, backtracking).

### Reflection / Self-Refine

- **https://github.com/langchain-ai/langgraph-reflection** — Official LangChain prebuilt reflection graph (185 stars). Loop: a "main" agent solves the task → a "critique" agent checks the work → if the critique returns a message, the main agent runs again; if it returns nothing, the graph finishes. State is a `MessagesState` list; termination = critique agent returns no critique. Runnable examples: `examples/llm_as_a_judge.py` (separate judge model with a `Finish` tool) and `examples/coding.py` (Pyright static analysis as the external evaluator).
- **https://www.langchain.com/blog/reflection-agents** — LangChain blog (2024-02-21) with three runnable Python implementations on one page: Simple Reflection (generate → critique → revise with a max-iteration guard), Reflexion, and LATS. Best for comparing the three loops side by side.

### Reflexion

- **https://github.com/emarco177/reflexion** — LangGraph implementation. Nodes: `draft` → `execute_tools` (Tavily search) → `revise`, with configurable max iterations (default 2). State = LangGraph message list; termination = iteration budget.
- **https://github.com/kargarisaac/reflexion** — smolagents-based implementation. `ReflexionAgent` wraps a `CodeAgent` with explicit trial-loop parameters: `max_trials` (termination), `max_reflections` (episodic memory — keeps the N most recent verbal reflections and injects them into the next trial's system prompt), `max_steps` per trial, and a user-supplied `success_criteria` string as the external success signal.

### ReAct

- **https://github.com/huggingface/smolagents** — Hugging Face's official agent library; `CodeAgent`/`ReactAgent` implement the ReAct loop with code as the action space. Loop: model emits thought + action (code), the tool executor runs it, the observation is appended to the message history, repeat until a final-answer marker or step cap.
- **https://til.simonwillison.net/llms/python-react-pattern** — Simon Willison's classic from-scratch ReAct (~50 lines): system prompt locking the Thought/Action/Observation grammar, a regex to extract `Action: tool: input`, a Python `dict` tool registry, and a `while` loop that stops when the model emits `Answer:`. The clearest minimal reference for how the loop is actually built.
- Also verified: **https://github.com/PeymanKh/react-agent-from-scratch** — zero-dependency OOP version.

### LATS

- **https://github.com/weill-labs/lats** — Clean-room reproduction. Domain-agnostic core in `lats/node.py` (UCT selection + backprop); two domains: HumanEval (MCTS over code, reward = fraction of self-generated unit tests passed) and HotPotQA (MCTS over ReAct trajectories with an LM value function). Termination = hidden-test pass or `max_iters` budget. Includes 44 API-free tests.
- **https://pypi.org/project/llama-index-agent-lats** — Official LlamaIndex integration (`llama-index-agent-lats`). `LATSAgentWorker` plugs into `AgentRunner` and implements the paper's select/expand/evaluate/backprop loop over tool-calling trajectories. The official LATS repo README points to this as the "general implementation for your AI applications."

### REWOO

- **https://github.com/pywind/rewoo-agent** — Modern async implementation. Planner emits a plan with `#E1`-style placeholders, an executor service runs tools (dependency-aware), a solver integrates results. State = plan + task models (`src/models/plan.py`, `task.py`); termination = solver produces the final answer after all placeholders are resolved.
- The LangGraph rewoo notebook (already in the prior list) remains the canonical reference; NVIDIA NeMo Agent Toolkit also ships a ReWOO agent: https://docs.nvidia.com/nemo/agent-toolkit/1.2/workflows/about/rewoo-agent.html

### RISE / STaR (training-time)

- **https://github.com/cmu-mind/RISE** — Official RISE codebase (34 stars). Built on FastChat; adds reward-weighted regression finetuning and multi-turn GSM8K/MATH evaluation. Loop: unroll the current model k-1 turns, sample an "improved" final turn (self-distillation or distillation from a stronger model), train on the multi-turn traces with reward-weighted regression, repeat. Termination = fixed number of iterations.
- **https://github.com/ezelikman/STaR** — Official STaR code (232 stars, NeurIPS 2022). `iteration_train.py` implements the bootstrap loop on mesh-transformer-jax: generate rationales → keep only those yielding correct answers (rationalize the rest given the correct answer) → finetune → repeat.
- Also verified: **https://github.com/raj-chinagundi/STaR-Self-Taught-Reasoner** — a modern GSM8k implementation comparing zero-shot CoT / vanilla SFT / STaR (the official repo is JAX-era).

### Self-Challenging

- **No public implementation exists.** Verified via the first author's GitHub (`yf-zhou`), a GitHub repo search, and a facebookresearch check. The paper (NeurIPS 2025, arXiv:2506.01716) describes the Code-as-Task (CaT) format — instruction + verification function + solution/failure cases — but the code was never released. Anyone implementing it must work from the paper.
- Closest related released code: **https://github.com/shenao-zhang/SELM** (Self-Exploring Language Models) — an online-alignment RL loop where the model generates its own preference data; same "self-generated training signal" family, but not the challenger/executor loop.

### SEAL

- **https://github.com/Continual-Intelligence/SEAL** — **Official MIT CSAIL repo for Self-Adapting Language Models** (1860 stars). Two domains (`knowledge-incorporation/`, `few-shot/`), each with code + data + docs. Loop (Algorithm 1 in the paper): sample (context, task) → model generates a self-edit (training data + update directives) → inner SFT/LoRA update → evaluate on the task → reward feeds an outer RL loop that improves self-edit generation. Termination = outer RL convergence.
- ⚠️ Name collision: **https://github.com/yihaohu0118/SEAL** is a _different_ paper ("Synergistic Co-Evolution of Agents and Learning Environments") — do not cite it as Self-Adapting LMs.

### Voyager

- **https://github.com/erlunlian/voyager-minecraft-ai** — LangGraph reimplementation. Explicit graph orchestration (`src/graph/voyager_graph.py`): Curriculum Agent proposes a task → Action Agent retrieves skills and writes JS code → Mineflayer bot executes → Critic Agent evaluates → successful code is stored in a ChromaDB skill library (semantic retrieval) → session state persisted to PostgreSQL. The clearest modern re-read of the Voyager loop.
- **https://github.com/anassee15/vision-voyager** — VLM-based reimplementation that adds vision to the Voyager agents (`voyager/agents/action.py`, `critic.py`, `curriculum.py`, `skill.py`), keeping the same skill-library + auto-curriculum structure.

### Multi-Agent Debate

- **https://github.com/HKUST-KnowComp/LLM-discussion** — Official code for the ACL 2024 paper "Rethinking the Bounds of LLM Reasoning: Are Multi-Agent Discussions the Key?" Pluggable discussion protocols in `src/rules/Debate/` (DebateLauncher, DebateRule — propose/critique rounds). Notable because it is the paper that _skeptically_ evaluated debate and found single-agent with strong prompts ≈ debate — worth reading before building a debate loop.
- **https://github.com/teddytennant/FUSION** — Multi-model debate CLI. Three phases: independent initial answers → N review rounds where each agent critiques the others' latest answers and emits a refined answer → a synthesizer agent merges final answers. Termination = fixed review-round count.

### STORM

- **https://github.com/stanford-oval/storm/blob/main/knowledge_storm/collaborative_storm/modules/co_storm_agents.py** — The Co-STORM agent code, now integrated into the main storm repo (EMNLP 2024). `CoStormExpert` (answers grounded in retrieval and/or raises follow-up questions), `SimulatedUser`, plus a Moderator that asks questions from undiscovered retrieved info; a dynamic mind map is the shared state. This is the multi-agent discourse loop on top of the STORM pipeline.
- Co-STORM paper: **https://arxiv.org/abs/2408.15232** — "Into the Unknown Unknowns: Engaged Human Learning through Participation in Language Model Agent Conversations".

### STO / SICA

- **https://github.com/MaximeRobeyns/self_improving_coding_agent** — **The official SICA implementation** (397 stars, ICLR 2025 SSI-FM workshop paper). This was missing from the prior comments (which said "no reliable repository for SICA"). Loop: evaluate current agent version on benchmark tasks → store results in an archive → run the agent on its own codebase to implement an improvement → re-benchmark, repeat. Meta-agent and target agent are the same system; observability via event bus + callgraph (`base_agent/src/events/`, `callgraph/`).
- **https://github.com/MrTsepa/micro-sica** — Minimal SICA. `sica_loop.py`: execute task → log outcome to `memory/study_log.json` → read own source + memory → ask the LLM "how can I improve?" → validate proposed code (ast.parse, py_compile, structural check, canary test) → human-in-the-loop approval gate → overwrite its own file. The smallest readable example of the self-rewrite loop with explicit safety gates.

---

## 3. Web search keywords used

### The 12 patterns (exact queries)

1. Reflection: `LangGraph evaluator-optimizer tutorial reflection agent implementation code`
2. Reflexion: `Reflexion agent implementation GitHub langchain reflexion agent notebook`
3. ReAct: `ReAct agent from scratch implementation GitHub thought action observation loop code`
4. LATS: `LATS language agent tree search implementation GitHub tree search agent`
5. REWOO: `REWOO plan execute agent implementation GitHub planner solver`
6. RISE: `RISE recursive introspection implementation GitHub cmu-mind`
7. STaR: `STaR self-taught reasoner implementation GitHub code bootstrapping reasoning`
8. Self-Challenging: `"Self-Challenging Language Model Agents" implementation code GitHub`
9. SEAL: `SEAL self-adapting language models code implementation GitHub`
10. Voyager: `Voyager Minecraft agent reimplementation GitHub skill library code`
11. Multi-Agent Debate: `multi-agent debate implementation GitHub LLM agents propose critique revise code`
12. STORM: `Co-STORM collaborative storm implementation GitHub code`
13. STO/SICA: `SICA self-improving coding agent implementation code GitHub`

### Related topics (exact queries)

- Process reward models: `process reward models PRM LLM agents arXiv Let's Verify Step by Step`
- Evaluator-optimizer: `Anthropic Building Effective Agents evaluator-optimizer pattern`
- Agent memory: `memory mechanisms LLM agents survey episodic semantic short-term long-term arXiv`
- Self-evolving agents: `self-evolving agents survey arXiv self-improvement LLM agents 2025`
- Checkpointing: `LangGraph persistence checkpointers durable execution resume agent state`
- Skill libraries: `LLM agent skill library growing tool library lifelong learning arXiv`
- Observability: `OpenTelemetry GenAI semantic conventions LLM observability tracing agents`
- Swarms / plan-execute: `agent swarms hierarchical multi-agent orchestration plan-and-execute pattern arXiv`
- Tree of Thoughts: `Tree of Thoughts deliberate problem solving arXiv 2305.10601`
- GraphRAG memory: `GraphRAG knowledge graph memory LLM agents arXiv`
- Durable execution: `durable execution Temporal LLM agents retry resume workflow`

---

## 4. Related topics discovered (with primary sources)

- **Process Reward Models (PRM)** — https://arxiv.org/abs/2305.20050 ("Let's Verify Step by Step"). PRMs score each intermediate step — exactly the per-step signal LATS/Reflexion-style tree search needs to prune branches.
- **Evaluator-optimizer pattern** — https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/evaluator_optimizer.ipynb. Production-form Self-Refine: a generator + an evaluator loop with a stop condition; the canonical engineering implementation of the "loop with feedback" pattern.
- **Agent memory survey** — https://arxiv.org/html/2602.06052v4. Categorizes episodic/semantic/short-term/long-term memory; directly relevant to what to persist between loop iterations.
- **Self-evolving agents survey** — https://arxiv.org/abs/2507.21046. Maps the self-improvement lineage (STaR → STO → SEAL/RISE/Self-Challenging) into one taxonomy.
- **LangGraph checkpointers** — https://docs.langchain.com/oss/python/langgraph/checkpointers. Concrete mechanism for persisting agent state across retries/resumes — the practical answer to "retry with persistent state" without building custom infra.
- **AutoSkill (skill library)** — https://arxiv.org/abs/2603.01145v2. Automates growing a Voyager-style skill library; generalizes the skill-library pattern beyond embodied agents.
- **OTel GenAI semantic conventions** — https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md. Standardized `gen_ai` spans that explicitly cover logical operations including retries — the vendor-neutral answer to "how do we see the loop".
- **VMAO (Plan-Execute-Verify-Replan)** — https://arxiv.org/html/2603.11445v2. A verifiable multi-agent orchestration pattern; a concrete instance of plan-and-execute with a verification stage.
- **Tree of Thoughts** — https://arxiv.org/abs/2305.10601 and https://github.com/princeton-nlp/tree-of-thought-llm. The search-over-thoughts ancestor of LATS.
- **MemGraphRAG** — https://arxiv.org/html/2606.00610. Knowledge-graph memory for agents; a specific implementation of the memory survey's long-term store.
- **Temporal durable execution** — https://docs.temporal.io/ai. Durable retries/resume for LLM workflows; the "retry loop with persistent state" pattern at infrastructure level.

### Cross-links between patterns

- **STaR → STO → SEAL/RISE/Self-Challenging are one lineage**: STO is by Zelikman (the STaR author), and SEAL/RISE/Self-Challenging all fine-tune on self-generated traces.
- **LATS is now a framework feature**: the official repo points to LangGraph/LlamaIndex implementations — tree-search agents are no longer custom code.
- **Evaluator-optimizer (Anthropic) is Self-Refine in production form** — the research pattern and the engineering pattern are the same loop.
- **Voyager's skill library ↔ AutoSkill**: AutoSkill automates what Voyager did manually — skill libraries are a reusable cross-domain pattern.
- **OTel GenAI spans cover retries** — observability of retry loops is standardized.

---

## 5. Proposed issues (new — beyond the previously proposed #120–#124)

Status check on the prior proposals: **#120 and #124 were implemented** (bounded evaluator loop + regression harness, via agent-todo PR #132 and agent-runner PR #5 / agent-todo PR #159). **#121, #122, #123 were explicitly rejected by the human** ("too complicated", "leave as is", "we don't need that") — do not re-propose them. The implemented pattern to build on is: _a deterministic validator script + a bounded retry loop + offline tests wired into `completion-check`_.

### Proposal 1 — PR-description evaluator-optimizer loop (Self-Refine)

**Problem.** `AGENTS.md` requires every PR description to link action runs that prove the change works and cover all changed code paths. The coordinator opens the PR itself, and `.github/workflows/opencode.yml` only posts run-result comments — nothing machine-checkable validates the PR description. Open issue #210 documents the symptom: agents "always proudly tell that CI ran" instead of linking their own evidence runs. #120 proved the validator + bounded-retry pattern for issue bodies; PR descriptions have no equivalent contract.
**Proposed change.** New `scripts/validate_pr_description.py` mirroring `scripts/validate_refined_issue.py` (prints a validation token, exits non-zero on rejection): checks at least one absolute action-run link, rejects bare "CI ran/passed" claims without a linked run, requires the AGENTS.md sections, reuses the hostile-text rejection pattern. In `.github/workflows/opencode.yml`, add a "Validate PR description" step after the coordinator succeeds; on rejection, re-invoke the coordinator with the rejection token (bounded to max 2 attempts, mirroring the retry loop in `refine-issues.yml`), then re-validate. New `scripts/test_validate_pr_description.py` (pytest), picked up by `completion-check`.
**How to verify.** pytest covers valid/invalid descriptions; a manual dispatch with a deliberately non-compliant description shows the retry loop firing; `./scripts/completion-check` passes.

### Proposal 2 — Reflexion-style retry for failed coordinator runs (persistent failure memory)

**Problem.** `.github/workflows/hourly-issue.yml` carries a `ponytail:` comment documenting that "the agent-running claim label is never removed by these workflows, so issues that fail, or succeed without closing, are permanently retired from selection". The coordinator runs once under a 120-min timeout; when it fails or times out, the issue stays `agent-running` forever and is never re-attempted. There is no mechanism to re-attempt a failed issue with knowledge of the previous attempt (Reflexion's multi-trial loop with persistent verbal memory).
**Proposed change.** In `.github/workflows/opencode.yml`, add a "Release claim on failure" step (when the coordinator outcome is not success): remove the `agent-running` label and post a structured failure-summary comment (issue number, run URL, exit status, branch pushed, what remained). The hourly candidate query already excludes `-label:agent-running`, so unlabeling makes failed issues re-selectable; extend the candidate prompt to include the failure-summary comment so the selector and coordinator carry the previous attempt's context. Instruct the selector (`.opencode/agent/issue-selector.md`, `scripts/issue-selection-tail.txt`) to prefer retrying a failed issue with a summary, bounded (e.g. at most one retry per issue per day).
**How to verify.** Dispatch a run that fails; check the issue is unlabeled and the failure summary is posted; the next hourly selection includes the summary in the prompt.

### Proposal 3 — Bounded self-critique step before reporting "completed" (Reflection)

**Problem.** The run-result comment in `.github/workflows/opencode.yml` reports "✅ completed" based solely on the coordinator process exit code. There is no critique pass between "the agent says done" and "the workflow reports completed" — the Reflection/Self-Refine pattern (generate → critique → revise) is absent at the workflow level.
**Proposed change.** After the coordinator step succeeds, add a bounded reflection step: run a second opencode invocation with a new `critic` agent (defined in `.opencode/agent/critic.md` in this repo, or in `bacluc/provision-machines`) that reviews the pushed diff and the coordinator's final comment against the issue's `## Goal`/`## How to implement` and AGENTS.md requirements. If the critique finds violations, re-invoke the coordinator with the critique text (bounded to max 2 revision rounds); only after a clean critique does the run-result comment say "completed". Record the critique result (e.g. a `critique.json` artifact) so the comment can state "completed after N revision rounds".
**How to verify.** A run where the coordinator omits evidence links → the critique catches it and the revision round adds them; the run-result comment reflects the revision.

### Proposal 4 — Voyager-style lessons-learned cache (persistent cross-run memory)

**Problem.** The repo has exactly one persistent cross-run memory: the model-availability cache issue. Everything else is forgotten between runs. The standing analysis task #206 repeatedly finds the same failure patterns (agents not testing `.github` changes, agents claiming CI ran, duplicate PRs). The research is explicit: Reflexion's key learning is "improvements are ephemeral unless reflections are persisted and reused".
**Proposed change.** A new cache issue in the todo repo (e.g. "agent lessons learned"), managed like the model-availability cache (auto-detected or via a new `AGENT_LESSONS_CACHE_ISSUE` variable). In `.github/workflows/opencode.yml`, a step appends a short structured lesson entry after each run (issue number, outcome, one-line lesson), trimmed to the last N entries. In `.github/workflows/hourly-issue.yml`, include the recent lessons in the selection prompt so the selector and coordinator condition on them (Voyager's "retrieve relevant skills"). Small script `scripts/append-lesson.py` + pytest tests.
**How to verify.** Two consecutive runs; the second run's selection prompt contains the first run's lesson; a test covers the append/trim logic.

### Proposal 5 — Checkpoint/resume for timed-out runs

**Problem.** The coordinator runs under `timeout "${COORDINATOR_TIMEOUT}m"` (default 120 min) in `.github/workflows/opencode.yml`. #206 asks why runs get stuck with zero output for 2 hours and why the agent doesn't push preliminary results so another agent or human could continue. A timed-out run's issue stays `agent-running` and any re-attempt starts from scratch.
**Proposed change.** On timeout/failure, the existing "Ensure work is pushed" step already pushes the branch; add a step that writes a machine-readable checkpoint (branch name, last milestone from the progress comment, remaining steps) into the issue comment or an `agent-run-state.json` committed on the branch. Add a resume path: when the coordinator prompt is generated, detect an existing checkpoint for the issue and build a "continue from checkpoint" prompt (checkout the branch, read the state, continue) instead of "implement from scratch". Depends on Proposal 2's unlabeling to make the issue re-selectable.
**How to verify.** A run with a short timeout override leaves a checkpoint; a re-dispatch with the resume prompt continues from the branch and completes.

### Priority ranking

1. **Proposal 1** — directly enforces AGENTS.md's core testing requirement, addresses the documented #210 symptom, follows the proven #120 validator+retry pattern; deterministic and cheap.
2. **Proposal 2** — fixes the documented "issues permanently retired" bug (the `ponytail:` comment in `hourly-issue.yml`) and answers #206's recurring "why didn't the agent continue" questions; small diff.
3. **Proposal 3** — makes "✅ completed" mean something; model-based, moderate cost.
4. **Proposal 4** — adds the repo's second persistent memory and targets the repeated failure patterns #206 keeps finding; reuses the proven cache-issue pattern.
5. **Proposal 5** — addresses the 2-hour-stuck runs, but is the most technically involved and depends on Proposal 2; defer until 2 lands.

---

## 6. Notable corrections and discoveries

1. **The official SICA repo exists and was missed**: `MaximeRobeyns/self_improving_coding_agent` (397 stars) is the paper's released code — the prior comment claimed no reliable SICA repository existed. Same for SEAL: `Continual-Intelligence/SEAL` (1860 stars) is the official MIT CSAIL release.
2. **Self-Challenging (arXiv:2506.01716) has no public implementation** — verified via the author's GitHub, a repo search, and a facebookresearch check. Anyone implementing it must work from the paper's Code-as-Task description; SELM is the closest related released code.
3. **Acronym collisions are a real hazard**: RISE = Recursive Introspection (`cmu-mind/RISE`) vs. Reinforcing Reasoning with Self-Verification; SEAL = Self-Adapting LMs (`Continual-Intelligence/SEAL`) vs. co-evolution (`yihaohu0118/SEAL`); STaR = Self-Taught Reasoner (`ezelikman/STaR`) vs. an unrelated CVPR 2026 GUI paper. Verify the README before citing.
4. **Prior proposals #121/#122/#123 were rejected by the human, not implemented** — only #120/#124 landed. The new proposals above build on the implemented validator+retry pattern and avoid the rejected directions.
5. **The OpenAI cookbook reflection example is dead (404)**; the LangChain blog "Reflection Agents" post is the better replacement since it bundles Simple Reflection + Reflexion + LATS code in one page.

---

## Sources (verified 2026-09-17)

- LangChain — "Reflection Agents" blog (2024-02-21): https://www.langchain.com/blog/reflection-agents
- LangChain — langgraph-reflection repo: https://github.com/langchain-ai/langgraph-reflection
- Hugging Face — smolagents: https://github.com/huggingface/smolagents
- Simon Willison — "A simple Python implementation of the ReAct pattern for LLMs" (2023): https://til.simonwillison.net/llms/python-react-pattern
- weill-labs — LATS clean-room reproduction: https://github.com/weill-labs/lats
- LlamaIndex — llama-index-agent-lats: https://pypi.org/project/llama-index-agent-lats
- pywind — rewoo-agent: https://github.com/pywind/rewoo-agent
- CMU MIND — RISE official code: https://github.com/cmu-mind/RISE
- Zelikman et al. — STaR official code: https://github.com/ezelikman/STaR
- MIT CSAIL — SEAL official code: https://github.com/Continual-Intelligence/SEAL
- erlunlian — Voyager LangGraph reimplementation: https://github.com/erlunlian/voyager-minecraft-ai
- HKUST-KnowComp — LLM-discussion (ACL 2024): https://github.com/HKUST-KnowComp/LLM-discussion
- Stanford Oval — Co-STORM agents: https://github.com/stanford-oval/storm/blob/main/knowledge_storm/collaborative_storm/modules/co_storm_agents.py
- Robeyns et al. — SICA official code: https://github.com/MaximeRobeyns/self_improving_coding_agent
- Lightman et al. — "Let's Verify Step by Step" (PRM): https://arxiv.org/abs/2305.20050
- Anthropic — evaluator-optimizer cookbook: https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/evaluator_optimizer.ipynb
- Memory survey: https://arxiv.org/html/2602.06052v4
- Self-evolving agents survey: https://arxiv.org/abs/2507.21046
- LangGraph checkpointers: https://docs.langchain.com/oss/python/langgraph/checkpointers
- AutoSkill: https://arxiv.org/abs/2603.01145v2
- OTel GenAI semantic conventions: https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md
- VMAO: https://arxiv.org/html/2603.11445v2
- Tree of Thoughts: https://arxiv.org/abs/2305.10601
- MemGraphRAG: https://arxiv.org/html/2606.00610
- Temporal AI docs: https://docs.temporal.io/ai

---

## Run status

- [x] Research complete (3 parallel research agents: link verification + additional implementations, search keywords + related topics, issue proposals)
- [x] Findings posted to this comment
- [x] `./scripts/completion-check` → PASS (prettier, actionlint, 14 node tests, 134 pytest tests)
- Issue bacluc-agent/agent-todo#76 left open (research deliverable only, no code changes)

Run ✅ completed: https://github.com/bacluc-agent/agent-runner/actions/runs/35271552395

**Archived comment 7/20** — @bacluc-agent — 2026-09-19T01:44:09Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738354546)

Run: https://github.com/bacluc-agent/agent-runner/actions/runs/35413028657 — model: opencode/muse-spark-1.3-contributor-free

Read: AGENTS.md

Research complement for bacluc-agent/agent-todo#76: DONE.

- Verified all 18 seed+repo URLs alive (curl -I 200, 2026-09-19).
- Posted complementing comment (15.5k chars, no dup of 2026-09-06/07 or 2026-09-17): https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738362214
- Covers PreFlect, REWOO, Voyager, DMAD-2026 disambiguation, STORM, RISE-2024 vs 2026, SEAL, SICA vs STO + 3 pseudo-code blocks.
- Issue left open, no branch/PR (research-only).

**Archived comment 8/20** — @bacluc-agent — 2026-09-19T01:45:34Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738362214)

## Scope: what this adds (vs prior comments)

Run: https://github.com/bacluc-agent/agent-runner/actions/runs/35413028657 — model: opencode/muse-spark-1.3-contributor-free

Read: AGENTS.md

This comment complements bacluc-agent/agent-todo#76 without repeating the 2026-09-06/07 survey (ReAct, Reflexion, LATS, REWOO, RISE/STaR, Self-Challenging, SEAL, Voyager, Debate, STORM, STO/SICA) or the 2026-09-17 continuation (example code per pattern, search keywords, link verification, proposals 1–5). New material here: **PreFlect** (prospective reflection, 2026 — not covered before), **DMAD-2026 vs DMAD-ICLR2025 disambiguation** (two different papers share the acronym), **RISE-2024 vs RISE-2026 footnote** (two different papers share the acronym), **SICA vs STO split** (prior comments treated them as one entry — they are distinct loops), fresh implementation notes from the skill-library README and the `knowledge-storm` package, and runnable pseudo-code for three loops. All 18 URLs below returned HTTP 200 via `curl -I -L` on 2026-09-19.

## Table: Pattern | Core Idea | Cost | How built (1-2 lines) | Key learning | Source

| Pattern                           | Core Idea                                                                                                     | Cost                                                 | How built                                                                                                                                                                                                                                   | Key learning                                                                                                                                                                                                                         | Source                                                                                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| PreFlect                          | Critique and fix the _plan before executing_ it, using distilled planning errors; re-plan at runtime on stall | Low-Med (+17.64% tokens vs base)                     | Plan → reflector checks plan against 3–5 distilled error patterns → revise → think-act-observe loop with re-plan trigger                                                                                                                    | Retrospective reflection wastes cost on irreversible actions; pre-execution critique gained +12pp GAIA pass@1 (46.06→58.18, GPT-4.1) and transfers across backbones (Gemini-2.5-pro 50.30→59.39)                                     | Wang et al. (2026), arXiv:2602.07187                                                                                                       |
| REWOO                             | Decouple reasoning from observations: plan all tool calls with `#E` placeholders, execute, then solve         | Low-Med (2 LLM calls regardless of tool count)       | Planner emits plan + workers (`Plan#E1…`) → dependency-aware executor substitutes results → Solver integrates                                                                                                                               | Separation cuts tokens (~64% vs ReAct per prior survey) but only when tool dependencies are predictable upfront; official repo is `AI-Natural-Language-Processing-Lab/ReWOO-…`, community fork `ayush9h/ReWOO`                       | Xu et al. (2023), arXiv:2305.07372                                                                                                         |
| Voyager                           | Lifelong embodied agent: auto-curriculum + code-skill library + iterative self-repair                         | Medium (GPT-4 code gen per task, amortized by reuse) | Curriculum proposes task → Action writes JS skill → Mineflayer executes → Critic judges → success stored as `skill/{code,description,skills.json,vectordb}`; only the `skill/` dir is the shareable library                                 | Skills as versioned code compose and transfer; community checkpoints are resumed via `skill_library_dir=<ckpt>`; prior 09-17 reimplementations (LangGraph/ChromaDB+Postgres, vision variant) confirm the pattern ports off Minecraft | Wang et al. (2023), arXiv:2305.16291; https://github.com/MineDojo/Voyager                                                                  |
| DMAD-2026                         | Debate fails from correlated errors; fix with diverse seeding + calibrated confidence                         | High (oversample N + GRPO training + debate rounds)  | Oversample N answers → greedily keep K most diverse by embedding distance → debate with GRPO-trained confidence scores that weight belief updates                                                                                           | Theory: vanilla debate is a martingale (expected correctness preserved); confidence-weighting makes it a submartingale (drifts toward correct); beats vanilla MAD and majority vote on 6 QA benchmarks                               | Zhu et al. (2026), arXiv:2601.19921; https://github.com/SpaceHunterInf/DMAD                                                                |
| STORM                             | Multi-perspective research synthesis: outline → retrieve → write with discourse                               | High (many retrieval+gen rounds)                     | Topic → perspective agents ask questions → retrieval → outline → section drafting with citations; Co-STORM adds Expert/SimulatedUser/Moderator + shared mind map                                                                            | Grounding every claim in retrieved sources is what separates it from free-form writing; ships as `pip install knowledge-storm` with live demo; Co-STORM discourse loop is the reusable part                                          | Shao et al. (2024); https://pypi.org/project/knowledge-storm; https://storm.genie.stanford.edu/                                            |
| RISE-2024 vs RISE-2026 (footnote) | Same acronym, different loops — do not conflate                                                               | Training cost (both)                                 | 2024: finetune on mistake→feedback→fix multi-turn traces so self-correction becomes internal. 2026: online RL (PPO/verl) jointly training solving + self-verification with verifiable rewards on-policy                                     | Rent-vs-buy applies: 2024 buys introspection into weights via traces; 2026 buys a verifier alongside the solver (+2.8× verification accuracy, Qwen2.5). Check the README before citing                                               | Qu et al. (2024), https://github.com/cmu-mind/RISE vs Liu et al. (2025), arXiv:2505.13445, https://github.com/xyliu-cs/RISE                |
| SEAL                              | Model authors its own training edits (data + update directives), outer RL rewards edits that help             | High (inner SFT/LoRA + outer RL)                     | Sample (context, task) → generate self-edit → inner update → evaluate → reward feeds outer loop (Algorithm 1)                                                                                                                               | Edits as natural language stay interpretable; 33.5→47% factual QA, 0→72.5% few-shot in paper; name collision with `yihaohu0118/SEAL` (co-evolution, unrelated)                                                                       | Zweiger et al., NeurIPS 2025; https://github.com/Continual-Intelligence/SEAL                                                               |
| SICA vs STO (split)               | STO: the _optimizer program_ improves itself. SICA: the _agent_ edits its own source gated by benchmarks      | High (repeated LLM + full re-eval loops)             | STO: seed improver → apply to downstream code → apply to itself, keep metric wins (rediscovers beam search/SA). SICA: benchmark → archive → self-edit own code → re-benchmark, keep wins; micro-SICA adds `ast.parse` + canary + human gate | Both need sandboxing + conservative acceptance (keep edit only on measured win) or they overfit/disable guards; STO improves the tool, SICA improves the agent — different blast radius                                              | STO: Zelikman et al., COLM 2024, arXiv:2310.02304. SICA: Robeyns et al. 2025, https://github.com/MaximeRobeyns/self_improving_coding_agent |

Footnotes: (a) DMAD-2026 (Zhu et al., diversity+confidence, `SpaceHunterInf/DMAD`) ≠ DMAD-ICLR2025 (Diverse MAD, distinct reasoning styles per agent, `MraDonkey/DMAD`) — same acronym, different fix for debate failure. (b) STO venue is COLM 2024 per the 09-07 correction — retained here.

## Commonalities (generate-critique-revise, persistent memory write-manage-read, tool-use loop)

1. **Generate-critique-revise is the shared skeleton.** PreFlect (plan critic), Reflexion (post-trial critic), STORM (perspective Q&A + drafting), DMAD-2026 (cross-agent critique), critic-in-the-loop — all instantiate draft → evaluate → revise with a budget. Zylos (2026-05-12) makes the mechanism precise: the loop only helps when the critique signal is _decorrelated_ from the generator (execution results, retrieval, a trained PRM, or a differently-prompted role).
2. **Persistent memory is write-manage-read, not just a log.** Voyager curates skills (`skills.json` + embeddings, community sharing), Reflexion keeps 1–3 verbal reflections, STORM keeps a mind map, SEAL distills edits into weights. The Towards-Data-Science memory guide and arXiv:2603.07670v1 agree: retention policy and retrieval beat raw accumulation.
3. **The tool-use loop grounds the critique.** Code execution (HumanEval 80→91% in Reflexion), test-shaped tasks (Self-Challenging CaT), retrieval grounding (Self-RAG tokens, STORM citations), verifier rewards (RISE-2026) — every reliable loop anchors judgment in something outside model priors. Intrinsic-only self-correction degrades reasoning (Huang et al., ICLR 2024).

## Differences (search vs linear, training vs prompting rent-vs-buy one-liner, intrinsic vs grounded, retrospective vs prospective)

- **Search vs linear:** LATS/DMAD fan out (tree, debate pool) then prune; REWOO/Reflexion follow one trajectory and repair it. Search costs 5–10× but recovers from early mistakes; linear is cheaper and wins when the first attempt is usually close.
- **Training vs prompting — rent-vs-buy one-liner:** prompting loops (PreFlect, Reflexion, critic-in-the-loop) _rent_ improvement per task with zero weight changes; training loops (RISE-2024/2026, STaR, SEAL, STO/SICA) _buy_ improvement into weights or code at high upfront cost that amortizes over many tasks.
- **Intrinsic vs grounded:** surface errors (format, style) yield to intrinsic critique; reasoning errors need grounded signals (tests, tools, PRMs) — the single most replicated finding across the seed sources.
- **Retrospective vs prospective:** everything before PreFlect reflects _after_ failure; PreFlect reflects _before_ acting, which matters exactly when actions are costly or irreversible (tool side effects, robot acts, published writes). Complement with runtime re-planning — foresight alone misses runtime-only constraints.

## Examples of loops in the wild (2-3 repo links + takeaways)

- **https://github.com/MineDojo/Voyager** (7.2k stars) — the skill-library README shows the durable artifact is just `skill/` (code + description + `skills.json` + vectordb); curriculum/qa/event dirs are session state. Takeaway: separate _shareable library_ from _ephemeral run state_; community checkpoints resume via one path variable.
- **https://github.com/SpaceHunterInf/DMAD** — debate bootstrapped from `data/example_debate_data.json` with `low_diversity`/`random`/`high_diversity` subsets, GRPO+LoRA in two stages (express confidence, then use others'). Takeaway: diversity is engineered at seeding time (embedding-distance selection), not hoped for at debate time.
- **https://github.com/MaximeRobeyns/self_improving_coding_agent** — evaluate → archive → self-edit → re-benchmark with event-bus/callgraph observability. Takeaway: the loop is only as trustworthy as its acceptance gate (benchmark delta) and its trace (what changed, why, measured effect).

## Pseudo-code (REWOO 40-line Plan-Execute-Solve, Voyager 50-line curriculum+skill library, critic-in-the-loop max_retries=2 with escalate)

REWOO Plan-Execute-Solve:

```python
def planner(task, tools):
    return llm(f"Plan for: {task}\nTools: {tools}\n"
               "Reply steps as: Plan: <what>\n#E1, #E2... = tool results needed")

def worker(step, evidence):
    tool, args = parse_tool_call(step)
    return TOOLS[tool](substitute(args, evidence))

def solver(task, plan, evidence):
    return llm(f"Task: {task}\nPlan: {plan}\nEvidence: {evidence}\nAnswer now.")

def rewoo(task, tools):
    plan, steps = planner(task, tools)
    evidence = {}
    for i, step in enumerate(steps):
        if needs_tool(step):
            evidence[f"#E{i+1}"] = worker(step, evidence)
    return solver(task, plan, evidence)
```

Voyager curriculum + skill library:

```python
library = SkillLib.load(dir)          # code + description + skills.json + vectordb
archive = {"done": [], "failed": []}

while True:
    task = curriculum_agent(propose=True, context=archive)
    skills = library.retrieve(task, k=5)
    code = action_agent(task, skills)
    result = mineflayer.execute(code)
    verdict = critic_agent(task, code, result)
    if verdict.ok:
        entry = skill_manager.compress(task, code)
        if self_check(entry):
            library.add(entry)
            archive["done"].append(task)
    else:
        code = action_agent(task, skills, feedback=verdict.critique)
        result = mineflayer.execute(code)
        if critic_agent(task, code, result).ok:
            library.add(skill_manager.compress(task, code))
        archive["failed"].append(task)
```

Critic-in-the-loop (`max_retries=2` with escalate):

```python
def agent_with_critic(task, max_retries=2):
    draft = agent(task)
    for attempt in range(max_retries + 1):
        critique = critic(task, draft)   # heuristic, LLM-judge, or grounded check
        if critique.accept:
            return draft
        if attempt == max_retries:
            return escalate(task, draft, critique)  # human queue, never silent fail
        draft = agent(task, draft=draft, feedback=critique.fixes)
```

## Sources APA-like with URLs

- Wang, H., Cao, Y., Lin, L., & Chen, J. (2026). PreFlect: From retrospective to prospective reflection in LLM agents. arXiv:2602.07187. https://arxiv.org/abs/2602.07187
- Zhu, X., Zhang, C., Chi, Y., Stafford, T., Collier, N., & Vlachos, A. (2026). Demystifying multi-agent debate: The role of confidence and diversity. arXiv:2601.19921. https://arxiv.org/abs/2601.19921
- Xu, B., et al. (2023). ReWOO: Decoupling reasoning from observations for efficient augmented language models. arXiv:2305.07372. https://github.com/AI-Natural-Language-Processing-Lab/ReWOO-Decoupling-Reasoning-from-Observations-for-Efficient-Augmented-Language-Models
- Wang, G., et al. (2023). Voyager: An open-ended embodied agent with LLMs. arXiv:2305.16291. https://github.com/MineDojo/Voyager
- Shao, Y., et al. (2024). STORM: Synthesis of topic outlines through multi-perspective question asking. https://pypi.org/project/knowledge-storm — demo https://storm.genie.stanford.edu/
- Liu, X., et al. (2025). Trust, but verify: A self-verification approach to RL with verifiable rewards (RISE-2026). arXiv:2505.13445. https://arxiv.org/abs/2505.13445
- Qu, C., et al. (2024). Recursive introspection: Teaching LLM agents how to self-improve (RISE-2024). https://github.com/cmu-mind/RISE
- Zweiger, et al. (2025). Self-adapting language models (SEAL). NeurIPS 2025. https://github.com/Continual-Intelligence/SEAL
- Robeyns, M., et al. (2025). SICA: A self-improving coding agent. https://github.com/MaximeRobeyns/self_improving_coding_agent
- Nakajima, Y. (2025). Better ways to build self-improving AI agents. https://yoheinakajima.com/better-ways-to-build-self-improving-ai-agents/
- Zylos Research. (2026a). AI agent reflection and self-evaluation patterns. https://zylos.ai/research/2026-03-06-ai-agent-reflection-self-evaluation-patterns
- Zylos Research. (2026b). Agent self-correction: From Reflexion to process reward models. https://zylos.ai/research/2026-05-12-agent-self-correction-reflexion-to-prm
- Appropri8. (2025). Reflexive AI agents. https://appropri8.com/blog/2025/11/10/reflexive-ai-agents/
- Emergent Mind. Reflection agent. https://www.emergentmind.com/topics/reflection-agent
- Agent Patterns Docs. Reflexion agent pattern. https://agent-patterns.readthedocs.io/en/stable/patterns/reflexion.html
- Towards Data Science. A practical guide to memory for autonomous LLM agents. https://towardsdatascience.com/a-practical-guide-to-memory-for-autonomous-llm-agents/
- Memory for autonomous LLM agents. (2026). arXiv:2603.07670. https://arxiv.org/html/2603.07670v1
- Eigent.ai. (2026). Self-evolved agents. https://www.eigent.ai/blog/self-evolved-agents

## Explicitly skipped

Re-deriving ReAct/LATS/Reflexion internals, re-listing the 09-17 example-code catalog and keyword queries, new issue proposals, and executing any repo code — all covered before or out of scope for a notes-only round. PreFlect's promised code drop (wwWhy725/PreFlect) was not yet public; numbers above are paper-reported, not reproduced.

Assumptions (non-interactive run): no human clarification sought; link liveness = `curl -I -L` HTTP 200 on 2026-09-19, not content re-review of every page; benchmark figures quoted from papers, not independently run. Upgrade path if heuristic: clone Voyager/DMAD/SICA and run their minimal examples to confirm the pseudo-code above, then post deltas as a follow-up comment.

**Archived comment 9/20** — @bacluc-agent — 2026-09-19T01:46:06Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738365340)

Run: https://github.com/agent-runner/agent-runner/actions/runs/35413028657 — model: opencode/muse-spark-1.3-contributor-free (tester)

Read: AGENTS.md

TEST RESULT: PASS — bacluc-agent/agent-todo#76 comment 5738362214 verified 2026-09-19.

- Comment exists (id 5738362214, 15372 chars / 15499 bytes, <65000), issue state OPEN (closed=false).
- Table: 8 data rows x 6 cols (PreFlect, REWOO, Voyager, DMAD-2026, STORM, RISE-2024/2026, SEAL, SICA/STO).
- Sections present: Scope, Table, Commonalities, Differences, 3 wild repos, 3 python pseudo-code blocks (REWOO/Voyager/critic max_retries=2+escalate), APA sources (19 URLs), Explicitly-skipped.
- Complements priors: PreFlect + arXiv:2601.19921 absent from all pre-09-19 comments (no duplication).
- URL liveness: 21/21 content URLs curl -I -L 200.
- completion-check: skipped (research-only, git status clean, no code touched).

**Archived comment 10/20** — @bacluc-agent — 2026-09-19T01:47:23Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738373133)

Run: https://github.com/bacluc-agent/agent-runner/actions/runs/35413028657 — model: muse-spark-1.3-contributor-free

Read: AGENTS.md

Review agent done for bacluc-agent/agent-todo#76. Verdict: APPROVED. Build comment https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738362214 complements priors (PreFlect/DMAD-2026/RISE-split/SICA-vs-STO all new, 0 prior mentions), 8-row x 6-col table, 3 wild repos with takeaways, 3 pseudo-code blocks incl. REWOO+Voyager+critic max_retries=2, 18 APA-like sources, assumptions/skipped/upgrade path stated, 15499 bytes < 65k, absolute refs used. No blocking issues; minor follow-ups only (18-vs-21 URL count wording, SEAL author string unverified).

**Archived comment 11/20** — @bacluc-agent — 2026-09-19T02:38:24Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738668445)

Run: https://github.com/bacluc-agent/agent-runner/actions/runs/35415994991 — model: opencode/muse-spark-1.2-contributor-free

Read: AGENTS.md

Branch: research/agent-patterns-76 — DONE (bacluc-agent/agent-todo#76)

✅ Synthesis posted: https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738708305 (13628 bytes, 12-row table, all 9 required URLs + 9 additional repos, accessed 2026-09-19)
✅ Traceability: https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5738711571 — empty commit 7ced46e on bacluc-agent/agent-runner@research/agent-patterns-76
✅ State: OPEN (no PR, research-only) — git status clean, /tmp/findings.md only, no new deps
