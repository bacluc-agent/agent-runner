# Research Notes: AI Agent Patterns (2026-09-24)

Research performed on 2026-09-24 for issue https://github.com/bacluc-agent/agent-todo/issues/76
Run: https://github.com/bacluc-agent/agent-runner/actions/runs/36032445045 (model: opencode/big-pickle)

## Search queries executed (fresh, 2026-09-24)

1. "AI agent design patterns survey 2026"
   -> arXiv:2605.13850v2 "A Two-Dimensional Framework for AI Agent Design Patterns: Cognitive Function x Execution Topology" (Huang & Zhou; v1 Mar 2026, v2 May 2026; 7x6 matrix, 28 patterns, 15 original names). VERIFIED via search.
2. "self-improving LLM agents research 2026"
   -> arXiv:2609.26457 "Recursive self-improvement of AI research agents" (AIDE^2; Srikanth, Zhao, Xu, Wu, Jiang; submitted 2026-09-22; autonomous 8-day run, 7 successive improvements; reward hacking 55%->32%; gains generalize to 4 held-out benchmarks). NEW - not in original candidate list.
3. "agent loop patterns September 2026 LLM orchestration"
   -> auditme.dev PAOVR Loop blog (2026-09-11; Plan -> Act -> Observe -> Verify -> Repair; production loop engineering; hard Verify->Repair gate). NEW.
4. "multi-agent debate DMAD 2026 research paper"
   -> aclanthology.org/2026.findings-acl.1694 "Demystifying Multi-Agent Debate: The Role of Confidence and Diversity" (= arXiv:2601.19921; vanilla MAD underperforms majority vote; diversity-aware init + confidence-modulated debate). VERIFIED.
5. "agentic AI survey 2026 taxonomy"
   -> Springer Cognitive Computation (2026-08-24) "From Language Models to Agentic AI: A Survey of Autonomous, Action-Enabled, and Collaborative LLM Agents" (4D taxonomy: autonomy, tool use, collaboration, safety-governance). NEW.
6. "SWE-agent coding agents 2026"
   -> aclanthology.org/2026.findings-acl.868 SWE-AGILE (Dynamic Reasoning Context + Reasoning Digests; 7B-8B SOTA on SWE-Bench-Verified with 2.2k trajectories; github.com/KDEGroup/SWE-AGILE). NEW.
7. "Voyager skill library 2026"
   -> only original github.com/MineDojo/Voyager (2023); no new source found.
8. "reflexion self-improvement agents 2026 follow-up"
   -> only original arXiv:2303.11366 (Reflexion); no new follow-up found via this query.
9. "When collaboration fails persuasion driven adversarial influence multi agent large language model debate" (follow-up to blocked pubmed URL)
   -> nature.com/articles/s41598-026-42705-7 "When collaboration fails: persuasion driven adversarial influence in multi agent large language model debate" (Scientific Reports, 2026-04-08; single adversarial agent lowers accuracy 10-40%, increases consensus on incorrect answers >30%; Best-of-N and RAG can amplify). VERIFIED.
10. "OpenAI practical guide to building AI agents business guide" (follow-up to 403 on openai.com)
    -> openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/ exists; content confirmed via search (single-agent, manager pattern, decentralized pattern, guardrails, human intervention). VERIFIED via search (direct fetch returns 403 bot protection).

## Sources verified by direct fetch (HTTP 200, accessed 2026-09-24)

- https://arxiv.org/abs/2607.13104 - Self-Improvements in Modern Agentic Systems: A Survey (Ren et al., 14 Jul 2026; system-level framework, update targets)
- https://aclanthology.org/2026.findings-acl.462/ - TT-SI: Self-Improving LLM Agents with Test-Time Training (Acikgoz, Qian, Ji, Hakkani-Tur, Tur; Findings ACL 2026)
- https://arxiv.org/abs/2608.00017 - Memory Reward Inflation in Self-Improving LLM Agents (Asadolahi et al., 29 Jun 2026; Echo Gap failure mode + LUCID fix)
- https://arxiv.org/abs/2607.05297 - MetaSkill-Evolve (Wang et al., 6 Jul 2026; two-timescale meta-skill evolution; recursive improvement)
- https://arxiv.org/abs/2607.13091 - Self-Improving AI Coding Agents Through Accumulated Behavioral Rules (Aggarwal & Ghalaty, 13 Jul 2026; 35+ service microservices platform, 5->18 rules)
- https://aclanthology.org/2025.emnlp-main.839/ - SAMULE (Ge et al., EMNLP 2025)
- https://arxiv.org/abs/2604.11378 - From Agent Loops to Structured Graphs: A Scheduler-Theoretic Framework for LLM Agent Execution (Hu Wei, 13 Apr 2026; SGH; position paper; survey of 70 systems trade-off analysis). NOTE: abstract does NOT state the "60% Agent Loop" figure - do not quote 60% unless verified in paper body.
- https://aclanthology.org/2026.acl-long.709/ - Latent Agents: Post-Training Procedure for Internalized Multi-Agent Debate (Yi, Mueller, Lee; ACL 2026)
- https://arxiv.org/abs/2606.13197 - ARMOR-MAD (Niu & Zhang, 11 Jun 2026; PAR/EASE/SOD; 65.5%/96.5%/90.0%/81.5%)
- https://arxiv.org/abs/2601.02854 - M3MAD-Bench (Li et al., v1 6 Jan 2026, v2 31 Jul 2026)
- https://aclanthology.org/2026.findings-acl.340/ - MADRA (Wang et al., Findings ACL 2026)
- https://arxiv.org/abs/2606.29270 - Minority Sentinel (He et al., 28 Jun 2026; Minority Truth phenomenon; LightGBM meta-classifier; Flip Precision 81.2%; AgentSearch Workshop @ SIGIR 2026)
- https://aclanthology.org/2026.findings-acl.1600/ - Free-MAD (verified via search results)
- https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns - AI Agent Orchestration Patterns (Azure Architecture Center; ms.date 2026-02-12, updated 2026-09-21; sequential, concurrent, group chat, handoff, magentic patterns)
- https://openai.github.io/openai-agents-python/multi_agent/ - Agent orchestration (OpenAI Agents SDK; LLM orchestration, handoffs, code orchestration)
- https://vercel.com/i/agent-orchestration-patterns - Agent orchestration patterns (2026-08-06; six patterns: single-agent loop, prompt chaining, routing, parallelization, orchestrator-worker, evaluator-optimizer; multi-agent up to 15x token volume; single-agent loops match/exceed multi-agent under equal compute budgets)
- https://machinelearningmastery.com/7-must-know-agentic-ai-design-patterns - 7 Must-Know Agentic AI Design Patterns (Bala Priya C, 2026-04-02; ReAct, Reflection, Planning, Tool Use, Multi-Agent Collaboration, Sequential Workflows, Human-in-the-Loop)
- https://www.jetbrains.com/pages/ai-agents/architecture/ai-agent-architecture - AI Agent Architecture Explained (JetBrains AI Agents for Developers Guide; ReAct, planner-executor, multiagent, stateful vs stateless; 46% of code AI-generated per JetBrains Developer Ecosystem Survey 2026)
- https://arxiv.org/abs/2609.26457 - Recursive self-improvement of AI research agents (AIDE^2; submitted 22 Sep 2026; 8-day run, 7 successive improvements; reward hacking 55%->32%)
- https://www.nature.com/articles/s41598-026-42705-7 - When collaboration fails: persuasion driven adversarial influence in multi agent large language model debate (Scientific Reports, 2026-04-08)
- https://agentpatterns.ai/patterns/agent-design/anthropic-effective-agents-framework/ - Anthropic Effective Agents Framework (URL moved from /agent-design/anthropic-effective-agents-framework/; redirect observed 2026-09-24)
- https://arxiv.org/abs/2601.19752 - Agentic Design Patterns: A System-Theoretic Framework (Jan 2026) - reported verified via search; re-confirm before citing if needed.

## URL issues encountered

- https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents - direct fetch returns 403 (bot protection); content verified via web search instead.
- https://pubmed.ncbi.nlm.nih.gov/41951693/ - blocked by cookie wall; use https://www.nature.com/articles/s41598-026-42705-7 instead.
- https://agentpatterns.ai/agent-design/anthropic-effective-agents-framework/ - redirects to https://agentpatterns.ai/patterns/agent-design/anthropic-effective-agents-framework/; use the new URL.
- https://cookbook.openai.com/examples/how_to_evaluate_and_refine_model_outputs - DEAD LINK (404); do not cite.

## Citation traps (do not reintroduce)

- ReWOO = arXiv:2305.18323 (Xu et al.) - NOT 2305.07372
- STO (Zelikman et al., arXiv:2310.02304) - venue is COLM 2024, not NeurIPS 2025
- SEAL = Zweiger et al., NeurIPS 2025 - NOT Hu et al. arXiv:2605.24426 (wrong citation appears 3x in corpus)
- RISE-2024 != RISE-2026
- DMAD-2026 (SpaceHunterInf/DMAD, diversity+confidence) != DMAD-ICLR2025 (Diverse MAD)
- PreFlect repo (wwWhy725/PreFlect) is empty - numbers from paper only
- Self-Challenging (arXiv:2506.01716) has no public implementation
- arXiv:2604.11378 abstract does not state the "60% Agent Loop" figure

## Proposed issues status (from corpus)

- #227 OPEN (ReAct loop demo), #228 OPEN (reflection evaluator-optimizer), #229 CLOSED (SWE-agent ACI), #230 OPEN (Voyager skill-library), #231 CLOSED (loop-termination metrics)
- #120/#124 implemented; #121/#122/#123 rejected by human