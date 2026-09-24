## Summary: AI Agent Patterns Research (2026-09-24)

Run: https://github.com/bacluc-agent/agent-runner/actions/runs/36032445045 — model: opencode/big-pickle
Read: AGENTS.md (agent-runner)

This comment consolidates the research on AI agent patterns gathered on this issue and adds fresh 2026-dated sources found today. The full comment history (20 comments) is archived verbatim in three closed issues: [part 1](https://github.com/bacluc-agent/agent-todo/issues/266) (comments 1–5), [part 2](https://github.com/bacluc-agent/agent-todo/issues/267) (comments 6–11), [part 3](https://github.com/bacluc-agent/agent-todo/issues/268) (comments 12–20).

### The 14 core patterns (carried over from earlier research)

| #   | Pattern                   | Core idea                                                                                 | Key source                                                                                                                                                                                            | Status                        |
| --- | ------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| 1   | Reflection / Self-Refine  | Generate → critique own output → revise until quality threshold                           | [Self-Refine (Madaan et al., arXiv:2303.17651)](https://arxiv.org/abs/2303.17651); [Anthropic Effective Agents](https://agentpatterns.ai/patterns/agent-design/anthropic-effective-agents-framework/) | carried over                  |
| 2   | Reflexion                 | Verbal self-feedback stored in episodic memory, no weight updates                         | [Shinn et al., arXiv:2303.11366](https://arxiv.org/abs/2303.11366)                                                                                                                                    | carried over                  |
| 3   | ReAct                     | Interleave Thought → Action → Observation in a loop                                       | [Yao et al., ICLR 2023, arXiv:2210.03629](https://arxiv.org/abs/2210.03629)                                                                                                                           | carried over                  |
| 4   | LATS                      | Language Agent Tree Search: MCTS over reasoning+action, reflection as value function      | [Zhou et al., arXiv:2310.04406](https://arxiv.org/abs/2310.04406)                                                                                                                                     | carried over                  |
| 5   | ReWOO                     | Reason Without Observation: decouple planning from tool execution                         | [Xu et al., arXiv:2305.18323](https://arxiv.org/abs/2305.18323)                                                                                                                                       | carried over                  |
| 6   | RISE / STaR               | Self-improvement via self-generated rationales (STaR) / recursive self-improvement (RISE) | [RISE, arXiv:2403.07815](https://arxiv.org/abs/2403.07815); [STaR, arXiv:2203.14465](https://arxiv.org/abs/2203.14465)                                                                                | carried over                  |
| 7   | SEAL                      | Self-Adapting LLMs: self-generated training data, self-evaluation, self-training          | [Zweiger et al., NeurIPS 2025](https://arxiv.org/abs/2605.24426)                                                                                                                                      | carried over                  |
| 8   | Voyager                   | LLM agent with growing skill library of executable code in Minecraft                      | [Wang et al., arXiv:2305.16291](https://arxiv.org/abs/2305.16291); [MineDojo/Voyager](https://github.com/MineDojo/Voyager)                                                                            | carried over                  |
| 9   | Multi-Agent Debate / DMAD | Multiple agents debate to improve answer quality                                          | [DMAD-2026 (SpaceHunterInf/DMAD)](https://github.com/SpaceHunterInf/DMAD); [Diverse MAD, ICLR 2025](https://arxiv.org/abs/2501.09906)                                                                 | carried over                  |
| 10  | STORM / Co-STORM          | Multi-perspective research: simulate expert discussion before writing                     | [Co-STORM, arXiv:2408.15201](https://arxiv.org/abs/2408.15201)                                                                                                                                        | carried over                  |
| 11  | Self-Challenging          | Agent challenges its own assumptions before acting                                        | [arXiv:2506.01716](https://arxiv.org/abs/2506.01716)                                                                                                                                                  | carried over (no public impl) |
| 12  | STO / SICA                | Self-Taught Optimizer: LLM improves its own optimizer code                                | [Zelikman et al., COLM 2024, arXiv:2310.02304](https://arxiv.org/abs/2310.02304)                                                                                                                      | carried over                  |
| 13  | PreFlect                  | Pre-reflection: critique plan before execution                                            | [wwWhy725/PreFlect](https://github.com/wwWhy725/PreFlect) (repo empty; paper numbers only)                                                                                                            | carried over                  |
| 14  | SWE-agent                 | Agent-Computer Interface (ACI) for repository-level coding                                | [Yang et al., arXiv:2405.15793](https://arxiv.org/abs/2405.15793)                                                                                                                                     | carried over                  |

### NEW research found 2026-09-24

**Taxonomy & frameworks**

- [A Two-Dimensional Framework for AI Agent Design Patterns (arXiv:2605.13850)](https://arxiv.org/abs/2605.13850) — cognitive function × execution topology, 7×6 matrix, 28 patterns, 15 original names (Huang & Zhou, v2 May 2026).
- [From Language Models to Agentic AI survey (Springer Cognitive Computation, 2026-08-24)](https://link.springer.com/article/10.1007/s12559-026-10500-0) — 4D taxonomy: autonomy, tool use, collaboration, safety-governance.
- [Agentic Design Patterns: A System-Theoretic Framework (arXiv:2601.19752)](https://arxiv.org/abs/2601.19752) — Jan 2026.
- [From Agent Loops to Structured Graphs (arXiv:2604.11378)](https://arxiv.org/abs/2604.11378) — scheduler-theoretic framework (SGH); position paper surveying 70 open-source agent systems (Hu Wei, Apr 2026).
- [Azure AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) — sequential, concurrent, group chat, handoff, magentic (updated 2026-09-21).
- [Vercel: Agent Orchestration Patterns (2026-08-06)](https://vercel.com/i/agent-orchestration-patterns) — six patterns: single-agent loop, prompt chaining, routing, parallelization, orchestrator-worker, evaluator-optimizer; multi-agent uses up to 15× tokens; under equal compute budgets single-agent loops match or exceed multi-agent accuracy.
- [JetBrains: AI Agent Architecture Explained](https://www.jetbrains.com/pages/ai-agents/architecture/ai-agent-architecture) — ReAct, planner-executor, multiagent, stateful vs stateless; runtime control/guardrails; 46% of code AI-generated (JetBrains Developer Ecosystem Survey 2026).
- [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) — single-agent, manager pattern, decentralized pattern, guardrails, human intervention.
- [MachineLearningMastery: 7 Must-Know Agentic AI Design Patterns (2026-04-02)](https://machinelearningmastery.com/7-must-know-agentic-ai-design-patterns) — ReAct, Reflection, Planning, Tool Use, Multi-Agent Collaboration, Sequential Workflows, Human-in-the-Loop.

**Self-improvement (2026 wave)**

- [Self-Improvements in Modern Agentic Systems: A Survey (arXiv:2607.13104)](https://arxiv.org/abs/2607.13104) — system-level framework, update targets (Ren et al., Jul 2026).
- [TT-SI: Self-Improving LLM Agents with Test-Time Training (Findings ACL 2026)](https://aclanthology.org/2026.findings-acl.462/) — Acikgoz et al.
- [Memory Reward Inflation in Self-Improving LLM Agents (arXiv:2608.00017)](https://arxiv.org/abs/2608.00017) — "Echo Gap" failure mode + LUCID fix (Asadolahi et al., Jun 2026).
- [MetaSkill-Evolve (arXiv:2607.05297)](https://arxiv.org/abs/2607.05297) — two-timescale meta-skill evolution (Wang et al., Jul 2026).
- [Self-Improving AI Coding Agents Through Accumulated Behavioral Rules (arXiv:2607.13091)](https://arxiv.org/abs/2607.13091) — 35+ service platform, 5→18 rules (Aggarwal & Ghalaty, Jul 2026).
- [SAMULE (EMNLP 2025)](https://aclanthology.org/2025.emnlp-main.839/) — Ge et al.
- [AIDE²: Recursive self-improvement of AI research agents (arXiv:2609.26457)](https://arxiv.org/abs/2609.26457) — autonomous 8-day run, 7 successive improvements; reward hacking drops 55%→32%; gains generalize to 4 held-out benchmarks (Srikanth et al., submitted 2026-09-22).

**Agent loops**

- [PAOVR Loop (auditme.dev, 2026-09-11)](https://auditme.dev/blog/paovr-loop) — Plan → Act → Observe → Verify → Repair; production loop engineering with a hard Verify→Repair gate.
- [OpenAI Agents SDK: Agent orchestration](https://openai.github.io/openai-agents-python/multi_agent/) — LLM orchestration, handoffs, code orchestration.

**Multi-agent debate (2026 wave)**

- [Demystifying Multi-Agent Debate: The Role of Confidence and Diversity (Findings ACL 2026)](https://aclanthology.org/2026.findings-acl.1694/) — vanilla MAD underperforms majority vote; diversity-aware init + confidence-modulated debate help.
- [Latent Agents: Internalized Multi-Agent Debate via Post-Training (ACL 2026)](https://aclanthology.org/2026.acl-long.709/) — Yi, Mueller, Lee.
- [ARMOR-MAD (arXiv:2606.13197)](https://arxiv.org/abs/2606.13197) — PAR/EASE/SOD; 65.5%/96.5%/90.0%/81.5% (Niu & Zhang, Jun 2026).
- [M3MAD-Bench (arXiv:2601.02854)](https://arxiv.org/abs/2601.02854) — Li et al., v2 Jul 2026.
- [MADRA (Findings ACL 2026)](https://aclanthology.org/2026.findings-acl.340/) — Wang et al.
- [Minority Sentinel (arXiv:2606.29270)](https://arxiv.org/abs/2606.29270) — "Minority Truth" phenomenon; LightGBM meta-classifier; Flip Precision 81.2% (He et al., Jun 2026; AgentSearch Workshop @ SIGIR 2026).
- [Free-MAD (Findings ACL 2026)](https://aclanthology.org/2026.findings-acl.1600/) — training-free MAD.
- [When collaboration fails: adversarial influence in MAD (Scientific Reports, 2026-04-08)](https://www.nature.com/articles/s41598-026-42705-7) — a single adversarial agent lowers accuracy 10–40% and increases consensus on incorrect answers >30%; Best-of-N and RAG can amplify the effect.

### Citation corrections (do not reintroduce the old errors)

- ReWOO = arXiv:2305.18323 (Xu et al.) — NOT 2305.07372.
- STO (Zelikman et al., arXiv:2310.02304) — venue is COLM 2024, not NeurIPS 2025.
- SEAL = Zweiger et al., NeurIPS 2025 — NOT "Hu et al., arXiv:2605.24426" (wrong citation appeared 3× in this issue's history).
- RISE-2024 ≠ RISE-2026; DMAD-2026 (SpaceHunterInf/DMAD) ≠ DMAD-ICLR2025 (Diverse MAD).
- PreFlect repo (wwWhy725/PreFlect) is empty — numbers come from the paper only.
- Self-Challenging (arXiv:2506.01716) has no public implementation.
- Dead link removed: cookbook.openai.com/examples/how_to_evaluate_and_refine_model_outputs (404).

### Cross-cutting findings

1. **Hard termination guard is non-negotiable** — every loop pattern needs a step ceiling: ReAct's classic failure mode (10 steps ≈ 50× token cost), Vercel's `stopWhen`/timeout budgets, JetBrains' stopping conditions, PAOVR's Verify→Repair gate.
2. **Separate reasoning from execution** — ReWOO, planner-executor (JetBrains), and SGH all decouple planning from acting; plans become inspectable artifacts.
3. **External feedback beats self-critique** — Reflexion, TT-SI, and Behavioral Rules all improve via external signals (tests, environment, accumulated rules), not just self-evaluation.
4. **Persistence/durable execution matters** — Vercel Workflows checkpoints every step; AIDE² discovered memory mechanisms to compress growing context.
5. **Vanilla MAD is fragile** — underperforms majority vote (Demystifying MAD) and is vulnerable to a single adversarial agent (Scientific Reports 2026).
6. **Self-improvement has failure modes** — Echo Gap (arXiv:2608.00017) and reward hacking (AIDE²: 55%→32% when explicitly monitored).

### Related issues

- [#227 (OPEN) ReAct loop demo](https://github.com/bacluc-agent/agent-todo/issues/227), [#228 (OPEN) reflection evaluator-optimizer](https://github.com/bacluc-agent/agent-todo/issues/228), [#229 (CLOSED) SWE-agent ACI](https://github.com/bacluc-agent/agent-todo/issues/229), [#230 (OPEN) Voyager skill-library](https://github.com/bacluc-agent/agent-todo/issues/230), [#231 (CLOSED) loop-termination metrics](https://github.com/bacluc-agent/agent-todo/issues/231).
- Implemented: #120, #124. Rejected by human: #121, #122, #123.

### Actions taken on this issue

- 10 fresh web searches + 20 verified sources (all accessed 2026-09-24; details in research notes committed to agent-runner branch `research/agent-patterns-76`).
- Archived all 20 comments verbatim into closed issues [#266](https://github.com/bacluc-agent/agent-todo/issues/266), [#267](https://github.com/bacluc-agent/agent-todo/issues/267), [#268](https://github.com/bacluc-agent/agent-todo/issues/268) (verified: closed, bodies < 65,536 chars, all comments verbatim).
- The 17 bot-generated comments on this issue will be deleted after this summary is posted; the 2 comments by @BacLuc and this run-tracking comment remain.
