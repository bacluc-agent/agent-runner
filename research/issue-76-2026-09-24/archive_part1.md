# Archive: issue #76 comments (2026-09-24) part 1/3

Source issue: https://github.com/bacluc-agent/agent-todo/issues/76
Archive date: 2026-09-24
Part: 1/3 — comments 1–5 of 20
Full archive: [part 1](https://github.com/bacluc-agent/agent-todo/issues/266) | [part 2](https://github.com/bacluc-agent/agent-todo/issues/267) | [part 3](https://github.com/bacluc-agent/agent-todo/issues/268)
Note: comments by @BacLuc (2) and the run-tracking comment (1) remain on the source issue.
Note: comment 20 (run-tracking) may have been updated after this snapshot.

---

**Archived comment 1/20** — @bacluc-agent — 2026-09-06T11:12:32Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5558831168)

## Research Findings: How Others Implemented Newer Agent Patterns (Loops)

I've conducted extensive research across the cited sources and additional materials. Below are the synthesized findings organized by pattern, with key learnings, commonalities, and differences.

---

### 1. ReAct (Reasoning + Acting)

**How it's built:** Interleaves Thought → Action → Observation in a loop. The model generates reasoning, calls a tool, receives the result, and decides the next step. Introduced by Yao et al. (ICLR 2023, arXiv:2210.03629).

**Implementation examples:**

- **From scratch (~50 lines of Python):** A system prompt locking the Thought/Action/Observation grammar, a regex parser for action extraction, a tool registry (dict), and a while loop with a stop condition. The Claude Agent SDK collapses this to ~10 lines with `query()` yielding messages as the agent thinks, calls tools, and observes results.
- **Production pattern:** A `ToolGateway` with allowlist, budget enforcement (`max_steps`, `max_tool_calls`, `max_seconds`), loop detection for repeated calls, and explicit `stop_reason` values. The policy boundary separates the model's decision from tool execution.

**Key learnings:**

- Each action is motivated by explicit reasoning — the agent doesn't call tools randomly
- The loop is the engine: seed messages → generate → record → branch on tool calls → guard with step ceiling
- **Main failure modes:** hallucinated tool names, infinite loops, quadratic token cost (every turn re-sends full history)
- Frameworks add streaming, retries, parallel tools, MCP servers — not the core loop
- ReAct optimizes the next action, not the full plan — lacks strategic foresight

**Common pitfall:** Without a hard step cap, the agent loops forever. With 10 steps, token cost is ~50x a 1-step task.

---

### 2. Reflexion / Reflection

**How it's built:** Generate → critique → revise, repeating until convergence. Reflexion (Shinn et al., 2023) adds persistent verbal memory across trials. The agent solves a task, sees failure, writes a natural-language critique, stores it, and tries again conditioned on that feedback.

**Implementation examples:**

- **ReflexionAgent** with 5 prompt roles: thinking, execution, reflection, documentation, and final generation
- Multi-trial cycle: Plan (using memory) → Execute → Evaluate → Reflect → Update Memory
- On HumanEval, verbal RL bumped pass@1 from GPT-4 baseline to ~91%
- **Self-Refine** (Madaan et al., 2023) uses the same generate→critique→revise pattern

**Key learnings:**

- No weight updates needed — cheap to adopt for any LLM
- Improvements are **ephemeral** unless reflections are persisted and reused
- The model can hallucinate bad reflections and reinforce them
- Per trial: ~4 LLM calls (plan, execute, evaluate, reflect). 3 trials = ~12 calls
- **Critical design decision:** termination condition — fixed iterations, quality threshold, convergence detection, or external verification

**Commonality with ReAct:** Both use the same Thought-Action-Observation loop, but Reflexion adds a self-critique step and persistent memory across trials.

---

### 3. LATS (Language Agent Tree Search)

**How it's built:** Lifts the agent loop into a Monte Carlo Tree Search. Each node is a partial trajectory. Uses UCT (Upper Confidence Bound for Trees) for selection, expansion, evaluation, and backpropagation. Published at ICML 2024.

**Implementation examples:**

- **LangGraph LATS notebook:** `Node` class with messages, reflection, parent/children, value, visits. `upper_confidence_bound()` balances exploitation vs exploration. `backpropagate()` updates scores up the tree.
- Four steps: Select (UCB) → Expand (generate candidates) → Evaluate (score) → Backpropagate
- 10 iterations × 4 calls = 40 LLM calls; 20 iterations = 80 calls

**Key learnings:**

- Explores multiple solution paths simultaneously rather than committing to one trajectory
- **Outperforms** simpler reflection because it can backtrack from failing branches
- Token cost is 5-10x ReAct — best reserved for high-stakes tasks
- The value function is hard to train without supervision signals
- **Key insight:** Self-consistency (sample many answers and vote) doesn't help agents that need to interleave tool calls with reasoning — LATS does

**Difference from ReAct:** ReAct follows a single chain; LATS explores a tree and backtracks.

---

### 4. REWOO (Reasoning WithOut Observation)

**How it's built:** Separates planning from execution. A Planner creates a complete plan with placeholders for tool results, all tools execute, then a Solver integrates results. Paper: Xu et al. (2023, arXiv:2305.18323).

**Implementation examples:**

- **Three phases:** (1) Worker creates plan with placeholders like `#E1`, `#E2` (2) Execute all solver requests, resolving dependencies (3) Worker integrates results
- Only **2 LLM calls** regardless of number of tools (plan + integrate) vs ReAct's N+1
- Achieves **5× token efficiency** and **4% accuracy improvement** on HotpotQA
- Can offload reasoning from 175B GPT-3.5 into 7B LLaMA via instruction tuning

**Key learnings:**

- **64% token reduction** vs ReAct across 6 public benchmarks, with 4.4% accuracy gain
- Cleaner reasoning: separation of planning and execution lets the model focus purely on logic
- Reduced hallucination: clear plan before execution
- **Limitation:** Only works when tool dependencies are predictable upfront
- Robust under tool-failure scenarios

**Difference from ReAct:** ReAct interleaves reasoning with each tool call; REWOO plans all upfront, executes all, then synthesizes.

---

### 5. Voyager (Skill Library + Auto-Curriculum)

**How it's built:** Three components: (1) automatic curriculum maximizing exploration, (2) ever-growing skill library of executable code, (3) iterative prompting with environment feedback, execution errors, and self-verification. Wang et al. (2023, arXiv:2305.16291).

**Implementation examples:**

- Skills stored as executable code programs indexed by embedding vectors
- Skill retrieval: query top-5 relevant skills from vector database
- Iterative code refinement: execute → get feedback/errors → refine → self-verify → commit to library
- **Results:** 3.3× more unique items, 2.3× longer distances, 15.3× faster tech tree mastery vs prior SOTA

**Key learnings:**

- Code as action space enables temporally extended, compositional, interpretable behaviors
- Skill library compounds capabilities — new skills built upon older ones
- **Without skill library, agent plateaus** — the library is pivotal for long-term improvement
- Self-verification agent acts as critic, checking success AND reflecting on mistakes
- Zero-shot generalization: skill library from one world transfers to new worlds

**Commonality with Reflexion:** Both use iterative feedback loops, but Voyager's loop is code-generation-focused with environment execution.

---

### 6. STORM (Multi-Perspective Research Synthesis)

**How it's built:** Breaks report generation into pre-writing (research + outline) and writing stages. Uses perspective-guided question asking and simulated conversations. Shao et al. (NAACL 2024).

**Implementation examples:**

- **Four modules:** Knowledge Curation → Outline Generation → Article Generation → Article Polishing
- **Perspective-Guided Question Asking:** Discovers diverse perspectives from existing articles
- **Simulated Conversation:** Writer and expert debate to refine understanding
- Co-STORM adds multi-agent discourse with Moderator, experts, and human user
- ~15-30 LLM calls per report, 72+ retrievals

**Key learnings:**

- Direct prompting leads to superficial questions — perspective-guided approach yields deeper coverage
- Multi-perspective analysis reveals insights single-view approaches miss
- **Major challenge:** source bias transfer and over-association of unrelated facts (not hallucination)
- Co-STORM's mind map helps reduce mental load during long discourse

---

### 7. Self-Challenging Agents

**How it's built:** Agent plays two roles — challenger (creates tasks with verified test code) and executor (solves them). RL on self-generated tasks doubles performance on tool-use benchmarks. Zhou et al. (NeurIPS 2025).

**Key learnings:**

- Fully label-free: no human annotations for tasks or rewards
- Tasks automatically scale with capability
- **Risk:** curriculum collapse — agent keeps generating tasks near its comfort zone

---

### 8. SICA / STO (Self-Improving Code Agents)

**How it's built:** Agent evaluates its own performance, enters self-edit phase using LLM to propose modifications to its own source code, re-evaluates, and keeps improvements. SICA reports 17-53% performance improvements.

**Key learnings:**

- Agent treats its own implementation as editable state
- Improvements persist and accumulate over time
- **Risk:** overfitting to benchmark, inadvertently disabling safety checks
- STO discovers classical search patterns (beam search, simulated annealing) without human guidance

---

## What Multiple Patterns Have in Common

1. **The loop is universal:** Every agent pattern is fundamentally a loop — generate → evaluate → improve. The difference is what's in the loop and how feedback is used.

2. **Memory/persistence is critical:** Patterns that persist learning across trials (Reflexion, Voyager, SiriuS) consistently outperform those that don't. Ephemeral reflection gives small gains; persistent memory gives compounding gains.

3. **External verification beats self-evaluation:** Patterns that use external signals (test results, environment feedback, tool outputs) are more reliable than those relying purely on the model's self-critique. Self-consistency traps and sycophantic reflection are real failure modes.

4. **Separation of concerns improves efficiency:** REWOO separates planning from execution; ReAct separates decision from tool execution; STORM separates research from writing. The pattern that separates "creator" and "critic" mindsets tends to be more reliable.

5. **Cost scales with exploration depth:** LATS and Reflexion are very expensive (many LLM calls); REWOO is cheap (2 calls); ReAct is medium. The choice of pattern is often a cost-quality tradeoff.

6. **Code as the action space enables compositional improvement:** Voyager and STO show that when skills/policies are represented as executable code, they can be composed, rewritten, and improved over time — much more tangible than ephemeral prompt tweaks.

7. **Termination conditions are non-negotiable:** Every loop-based pattern needs explicit stopping criteria — fixed iterations, quality thresholds, convergence detection, or external verification. Without them, loops degrade quality or run indefinitely.

---

## What They Did Differently

| Dimension            | ReAct            | Reflexion                   | LATS              | REWOO                    | Voyager           | STORM             |
| -------------------- | ---------------- | --------------------------- | ----------------- | ------------------------ | ----------------- | ----------------- |
| **Exploration**      | Single path      | Sequential trials           | Tree search       | Plan upfront             | Curriculum-driven | Multi-perspective |
| **Memory**           | None             | Verbal memory across trials | Tree values       | Placeholders             | Skill library     | Retrieved sources |
| **Feedback**         | Tool observation | Self-critique               | Value function    | Tool results             | Environment       | Retrieval         |
| **Cost**             | Medium           | Very High                   | Very High         | Low-Medium               | Medium            | Very High         |
| **Best for**         | Tool interaction | Learning from failures      | Complex reasoning | Cost-efficient workflows | Lifelong learning | Research reports  |
| **Self-improvement** | None             | Ephemeral                   | Via search        | None                     | Persistent skills | None              |

---

## Key Takeaways for Implementation

1. **Start simple:** ReAct or Reflection for quick wins. Add complexity only when needed.
2. **Persist learning:** The biggest performance gains come from storing and reusing experience (Reflexion memory, Voyager skill library, SiriuS experience bank).
3. **Verify externally:** Ground reflection in tool results, test outputs, or environment feedback — not just the model's self-critique.
4. **Separate planning from execution:** REWOO's approach of planning all upfront and executing in batch is dramatically more efficient when dependencies are predictable.
5. **Represent skills as code:** When agents can edit their own code/policies (STO, SICA, Voyager), improvements compound and persist.
6. **Budget everything:** Every loop needs hard limits on steps, time, tokens, and cost. Without them, agents will drift indefinitely.
7. **Curriculum diversity matters:** Self-generated tasks/experiences must be curated for diversity to avoid collapse into the agent's comfort zone.

---

## Sources

- **Yohei Nakajima** — "Better Ways to Build Self-Improving AI Agents" (yoheinakajima.com, Dec 2025) — Synthesizes NeurIPS 2025 work on self-improving agents
- **Agent Patterns Docs** — Reflexion Agent Pattern (agent-patterns.readthedocs.io) — Complete implementation guide with LangGraph
- **Zylos Research** — "AI Agent Reflection and Self-Evaluation Patterns" (Mar 2026) — Comprehensive survey of reflection patterns
- **Yao et al.** — "ReAct: Synergizing Reasoning and Acting in Language Models" (ICLR 2023, arXiv:2210.03629)
- **Shinn et al.** — "Reflexion: Language Agents with Verbal Reinforcement Learning" (2023, arXiv:2303.11366)
- **Xu et al.** — "ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models" (2023, arXiv:2305.18323)
- **Zhou et al.** — "Language Agent Tree Search Unifies Reasoning, Acting, and Planning" (ICML 2024, arXiv:2310.04406)
- **Wang et al.** — "Voyager: An Open-Ended Embodied Agent with Large Language Models" (2023, arXiv:2305.16291)
- **Shao et al.** — "STORM: Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking" (NAACL 2024)
- **Zhou et al.** — "Self-Challenging Language Model Agents" (NeurIPS 2025)
- **Robeyns et al.** — "SICA: A Self-Improving Coding Agent" (2025, OpenReview)
- **Growth Engineer** — "Implement the ReAct Pattern in 50 Lines of Python" (May 2026)
- **QubitTool** — "ReAct Agent Pattern: Production Loop and Safety Guide" (Apr 2026)
- **Agent Engineering** — "The ReAct Pattern" (Feb 2026)
- **DEV Community** — "The ReAct Loop From Scratch" (Jul 2026)
- **Stanford-oval** — STORM project (github.com/stanford-oval/storm)
- **Minedojo** — Voyager project (github.com/minedojo/voyager)
- **Zylos Research** — "Agent Self-Correction: From Reflexion to Process Reward Models" (May 2026)
- **Emergent Mind** — "Reflection Agent: Self-Correcting AI"
- **arXiv** — "Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers" (arXiv:2603.07670)
- **Appropri8** — "Reflexive AI Agents: Closing the Loop Between Perception and Self-Evaluation" (Nov 2025)
- **Towards Data Science** — "A Practical Guide to Memory for Autonomous LLM Agents"
- **Eigent.ai** — "Self-Evolved Agents: How AI Improves Itself"

**Archived comment 2/20** — @bacluc-agent — 2026-09-07T08:53:07Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5568005218)

## Updated Research Findings: All 12 Agent Patterns

This is an updated comprehensive research covering all patterns from the issue, with newly researched sections for **RISE/STaR**, **SEAL**, and **Multi-Agent Debate**. Sources have been fetched and verified from the URLs cited in the issue.

---

### 1. ReAct (Reasoning + Acting)

**Core idea:** Interleaves Thought → Action → Observation in a loop. The model generates reasoning, calls a tool, receives the result, and decides the next step.

**Cost:** Medium (~N+1 LLM calls for N steps)

**How it's built:** A system prompt locking the Thought/Action/Observation grammar, a regex parser for action extraction, a tool registry, and a while loop with a stop condition. The Claude Agent SDK collapses this to ~10 lines with `query()` yielding messages as the agent thinks, calls tools, and observes results.

**Key learnings:**

- Each action is motivated by explicit reasoning — the agent doesn't call tools randomly
- **Main failure modes:** hallucinated tool names, infinite loops, quadratic token cost (every turn re-sends full history)
- ReAct optimizes the next action, not the full plan — lacks strategic foresight
- Without a hard step cap, the agent loops forever. With 10 steps, token cost is ~50x a 1-step task.

**Source:** Yao et al. (ICLR 2023, arXiv:2210.03629)

---

### 2. Reflexion / Reflection

**Core idea:** Generate → critique → revise, repeating until convergence. Reflexion adds persistent verbal memory across trials.

**Cost:** Very High (4 LLM calls per trial × N trials)

**How it's built:** The agent solves a task, sees failure, writes a natural-language critique, stores it, and tries again conditioned on that feedback. On HumanEval, verbal RL bumped pass@1 from GPT-4 baseline to ~91%.

**Key learnings:**

- No weight updates needed — cheap to adopt for any LLM
- Improvements are **ephemeral** unless reflections are persisted and reused
- The model can hallucinate bad reflections and reinforce them
- **Critical design decision:** termination condition — fixed iterations, quality threshold, convergence detection, or external verification

**Common pitfall:** Without external verification, intrinsic self-correction is unreliable for reasoning errors (Huang et al., ICLR 2024: "LLMs Cannot Self-Correct Reasoning Yet"). Grounded self-correction (execution feedback, test results) is dramatically more reliable.

**Source:** Shinn et al. (2023, arXiv:2303.11366); Huang et al. (ICLR 2024, arXiv:2310.01798)

---

### 3. LATS (Language Agent Tree Search)

**Core idea:** Lifts the agent loop into a Monte Carlo Tree Search. Each node is a partial trajectory. Uses UCT for selection, expansion, evaluation, and backpropagation.

**Cost:** Very High (40-80+ LLM calls for 10-20 iterations)

**Key learnings:**

- Explores multiple solution paths simultaneously rather than committing to one trajectory
- **Outperforms** simpler reflection because it can backtrack from failing branches
- Token cost is 5-10x ReAct — best reserved for high-stakes tasks
- Self-consistency (sample many answers and vote) doesn't help agents that need to interleave tool calls with reasoning — LATS does

**Difference from ReAct:** ReAct follows a single chain; LATS explores a tree and backtracks.

**Source:** Zhou et al. (ICML 2024, arXiv:2310.04406)

---

### 4. REWOO (Reasoning WithOut Observation)

**Core idea:** Separates planning from execution. A Planner creates a complete plan with placeholders for tool results, all tools execute, then a Solver integrates results.

**Cost:** Low-Medium (only 2 LLM calls regardless of number of tools)

**Key learnings:**

- **64% token reduction** vs ReAct across 6 public benchmarks, with 4.4% accuracy gain
- Cleaner reasoning: separation of planning and execution lets the model focus purely on logic
- **Limitation:** Only works when tool dependencies are predictable upfront
- Robust under tool-failure scenarios

**Difference from ReAct:** ReAct interleaves reasoning with each tool call; REWOO plans all upfront, executes all, then synthesizes.

**Source:** Xu et al. (2023, arXiv:2305.18323)

---

### 5. RISE (Recursive Introspection)

**Core idea:** Fine-tunes models on multi-turn traces where an initial answer is wrong, feedback arrives, and a corrected answer follows. After training, the model can simulate this introspection loop internally at inference time.

**Cost:** High (training cost + multi-turn inference)

**How it's built:** RISE converts single-turn problems into multi-turn MDPs. The state is the prompt + history of prior attempts + optional feedback. Data is collected by unrolling the current model k-1 times followed by an improved version (via self-distillation or distillation from a more capable model). Training uses reward-weighted regression.

**Key learnings:**

- Self-correction becomes a **built-in capability** after training, not just a prompt trick
- RISE enables Llama2, Llama3, and Mistral models to improve themselves with more turns on math reasoning tasks
- On GSM8K, RISE improves LLaMa3-8B by 8.2% and Mistral-7B by 6.6% entirely using their own data
- RISE attains a 17.7% improvement for LLaMa2-7B over 5-turn introspection (outperforming parallel sampling from the first turn)
- GPT-3.5 itself only improves by 4.6% over five turns — RISE-trained smaller models outperform it
- **Key insight:** Simply imitating multi-turn data from other models is NOT sufficient — the model must learn from its own error distribution

**Difference from Reflexion:** RISE trains the model itself to self-correct (weight updates), while Reflexion uses verbal memory at inference time without changing weights.

**Source:** Qu et al. (NeurIPS 2024, arXiv:2407.18219); Zelikman et al. (2022) — STaR: Self-Taught Reasoner

---

### 6. SEAL (Self-Adapting Language Models)

**Core idea:** The model generates its own "self-edits" — natural-language instructions that specify training data and optimization hyperparameters for updating its own weights. These self-edits are learned via RL where the reward is downstream performance of the updated model.

**Cost:** High (training cost, RL loop with SFT inner loop)

**How it's built:** SEAL operates with two nested loops: an outer RL loop that optimizes self-edit generation, and an inner update loop that uses the generated self-edit to update the model via gradient descent. The model produces a self-edit SE, updates parameters via SFT: θ' ← SFT(θ, SE), evaluates performance, and uses the reward to improve the self-edit generation policy.

**Key learnings:**

- On factual QA (SQuAD no-passage), SEAL improves accuracy from 33.5% → 47%
- Self-generated data from SEAL **outperforms synthetic data generated by GPT-4.1**
- On few-shot learning (ARC-AGI subset), SEAL enhances performance over both standard ICL and self-editing without RL
- The model effectively becomes a **co-author of its own training set**
- Edits are **interpretable** as natural language, making debugging easier than black-box weight updates
- **Risk:** self-reinforcing biases if evaluation signal is misaligned; requires training pipeline in the loop

**Difference from RISE:** RISE trains models to self-correct reasoning traces; SEAL trains models to generate their own fine-tuning data and hyperparameters for weight updates.

**Source:** Zweiger et al. (NeurIPS 2025); Hu et al. (2026, arXiv:2605.24426)

---

### 7. Voyager (Skill Library + Auto-Curriculum)

**Core idea:** Three components: (1) automatic curriculum maximizing exploration, (2) ever-growing skill library of executable code, (3) iterative prompting with environment feedback, execution errors, and self-verification.

**Cost:** Medium

**Key learnings:**

- Code as action space enables temporally extended, compositional, interpretable behaviors
- Skill library compounds capabilities — new skills built upon older ones
- **Without skill library, agent plateaus** — the library is pivotal for long-term improvement
- 3.3× more unique items, 2.3× longer distances, 15.3× faster tech tree mastery vs prior SOTA
- Zero-shot generalization: skill library from one world transfers to new worlds

**Source:** Wang et al. (2023, arXiv:2305.16291)

---

### 8. Multi-Agent Debate (MAD)

**Core idea:** Multiple agents independently propose solutions, critique each other's proposals, and over multiple rounds converge on a shared, higher-quality answer. A moderator or judge agent steers the discussion.

**Cost:** High (3-6x token cost vs single agent; sequential rounds increase latency)

**How it's built:** The canonical flow is: (1) Proposal round — 2+ agents answer independently with different prompts/models; (2) Critique round — each agent receives others' proposals and names weaknesses; (3) Revision round — agents rework answers based on critique; (4) Consensus/decision — converge or moderator selects final answer.

**Key learnings:**

- **Diversity is critical:** Vanilla MAD with homogeneous agents often underperforms simple majority vote. Diversity-aware initialization (selecting diverse candidate answers) improves the prior probability of success (ACL 2026 Findings).
- **Confidence matters:** Confidence-modulated debate (agents express calibrated confidence and condition updates on others' confidence) breaks the martingale limitation and allows beliefs to drift toward correctness.
- **Mode collapse risk:** The critic reflexively agrees instead of naming genuine weaknesses → debate degenerates into expensive echoing.
- **Echo chamber risk:** Agents mutually reinforce a false premise. Countermeasure: diversify sub-agents with different models/prompts.
- **DMAD (Diverse Multi-Agent Debate):** Assigns distinct reasoning methods (IO, CCoT, CoT, etc.) to each agent, breaking "fixed mental set." DMAD in 2 rounds achieves higher performance than standard MAD in 5 rounds (ICLR 2025).
- **Meta-Moderator:** A learnable framework that dynamically regulates debate and decides when to finalize an answer, outperforming fixed-budget and agreement-based stopping (arXiv:2608.23029).
- In Anthropic's taxonomy (Building Effective Agents, Dec 2024), MAD belongs to the Evaluator-Optimizer pattern.

**Difference from Reflexion:** Reflexion is single-agent self-critique; MAD uses multiple agents critiquing each other, decorrelating error modes.

**Sources:** Du et al. (2024); Chan et al. (2024); Liang et al. (2024); ACL 2026 Findings (arXiv); ICLR 2025 DMAD; arXiv:2607.26212 (survey of 141 MAD studies); Blck Alpaca (2026)

---

### 9. STORM (Multi-Perspective Research Synthesis)

**Core idea:** Breaks report generation into pre-writing (research + outline) and writing stages. Uses perspective-guided question asking and simulated conversations.

**Cost:** Very High (~15-30 LLM calls per report, 72+ retrievals)

**Key learnings:**

- Direct prompting leads to superficial questions — perspective-guided approach yields deeper coverage
- Multi-perspective analysis reveals insights single-view approaches miss
- **Major challenge:** source bias transfer and over-association of unrelated facts
- Co-STORM adds multi-agent discourse with Moderator, experts, and human user

**Source:** Shao et al. (NAACL 2024); Stanford-oval/storm on GitHub

---

### 10. Self-Challenging Agents

**Core idea:** Agent plays two roles — challenger (creates tasks with verified test code) and executor (solves them). RL on self-generated tasks doubles performance on tool-use benchmarks.

**Cost:** High

**Key learnings:**

- Fully label-free: no human annotations for tasks or rewards
- Tasks automatically scale with capability
- **Risk:** curriculum collapse — agent keeps generating tasks near its comfort zone

**Source:** Zhou et al. (NeurIPS 2025)

---

### 11. STO / SICA (Self-Improving Code Agents)

**Core idea:** Agent evaluates its own performance, enters self-edit phase using LLM to propose modifications to its own source code, re-evaluates, and keeps improvements.

**Cost:** High

**Key learnings:**

- **STO** discovers classical search patterns (beam search, simulated annealing) without human guidance by applying the improver to its own code recursively
- **SICA** reports 17-53% performance improvements on coding tasks through self-edit loop
- Agent treats its own implementation as editable state — improvements persist and accumulate
- **Risk:** overfitting to benchmark, inadvertently disabling safety checks

**Sources:** Zelikman et al. (NeurIPS 2025 — STO); Robeyns et al. (2025 — SICA)

---

## What All 12 Patterns Have in Common

1. **The loop is universal:** Every agent pattern is fundamentally a loop — generate → evaluate → improve. The difference is what's in the loop and how feedback is used.

2. **Memory/persistence is critical:** Patterns that persist learning across trials (Reflexion memory, Voyager skill library, RISE training, SEAL self-edits) consistently outperform those that don't. "The gap between 'has memory' and 'does not have memory' is often larger than the gap between different LLM backbones" (arXiv:2603.07670).

3. **External verification beats self-evaluation:** Patterns that use external signals (test results, environment feedback, tool outputs) are more reliable than those relying purely on the model's self-critique. Intrinsic self-correction is unreliable for reasoning errors (Huang et al., ICLR 2024).

4. **Separation of concerns improves efficiency:** REWOO separates planning from execution; ReAct separates decision from tool execution; STORM separates research from writing. Separating "creator" and "critic" mindsets tends to be more reliable.

5. **Cost scales with exploration depth:** LATS, Reflexion, and STORM are very expensive; REWOO is cheap (2 calls); ReAct is medium. The choice of pattern is often a cost-quality tradeoff.

6. **Code as the action space enables compositional improvement:** Voyager and STO show that when skills/policies are represented as executable code, they can be composed, rewritten, and improved over time.

7. **Termination conditions are non-negotiable:** Every loop-based pattern needs explicit stopping criteria. Without them, loops degrade quality or run indefinitely.

8. **Diversity prevents echo chambers:** Multi-Agent Debate research shows that homogeneous agents converge on wrong answers. Diverse reasoning methods, models, or prompts are essential for debate to work.

9. **Training on self-correction traces creates lasting improvement:** RISE and SEAL show that training models on their own error-correction patterns produces capabilities that persist beyond any single inference session.

---

## What They Did Differently

| Dimension            | ReAct            | Reflexion              | LATS              | REWOO                    | RISE                     | SEAL                 | Voyager           | MAD                   | STORM             |
| -------------------- | ---------------- | ---------------------- | ----------------- | ------------------------ | ------------------------ | -------------------- | ----------------- | --------------------- | ----------------- |
| **Exploration**      | Single path      | Sequential trials      | Tree search       | Plan upfront             | Multi-turn MDP           | Self-edit RL         | Curriculum-driven | Multi-agent debate    | Multi-perspective |
| **Memory**           | None             | Verbal memory          | Tree values       | Placeholders             | Trained weights          | Self-edits           | Skill library     | Shared context        | Retrieved sources |
| **Feedback**         | Tool observation | Self-critique          | Value function    | Tool results             | Training reward          | Downstream perf.     | Environment       | Cross-agent critique  | Retrieval         |
| **Cost**             | Medium           | Very High              | Very High         | Low-Medium               | High (training)          | High (training)      | Medium            | High (3-6x)           | Very High         |
| **Best for**         | Tool interaction | Learning from failures | Complex reasoning | Cost-efficient workflows | Built-in self-correction | Model adaptation     | Lifelong learning | High-stakes decisions | Research reports  |
| **Self-improvement** | None             | Ephemeral              | Via search        | None                     | Trained into weights     | Trained into weights | Persistent skills | Via debate            | None              |

---

## Key Takeaways for Implementation

1. **Start simple:** ReAct or Reflection for quick wins. Add complexity only when needed.
2. **Persist learning:** The biggest gains come from storing and reusing experience (Reflexion memory, Voyager skill library, RISE/SEAL training).
3. **Verify externally:** Ground reflection in tool results, test outputs, or environment feedback — not just the model's self-critique.
4. **Separate planning from execution:** REWOO's approach is dramatically more efficient when dependencies are predictable.
5. **Represent skills as code:** When agents can edit their own code/policies (STO, SICA, Voyager), improvements compound and persist.
6. **Budget everything:** Every loop needs hard limits on steps, time, tokens, and cost.
7. **Diversify for debate:** Multi-Agent Debate only works with diverse agents, models, or reasoning methods. Homogeneous debate underperforms majority vote.
8. **Train on self-correction:** RISE and SEAL show that training models on their own error patterns creates durable self-improvement capabilities.
9. **Consider the cost-quality tradeoff:** REWOO (2 calls) vs LATS (40+ calls) — pick the pattern that matches your task's stakes.

---

## Sources

**Papers:**

- Yao et al. — "ReAct: Synergizing Reasoning and Acting in Language Models" (ICLR 2023, arXiv:2210.03629)
- Shinn et al. — "Reflexion: Language Agents with Verbal Reinforcement Learning" (2023, arXiv:2303.11366)
- Huang et al. — "Large Language Models Cannot Self-Correct Reasoning Yet" (ICLR 2024, arXiv:2310.01798)
- Zhou et al. — "Language Agent Tree Search Unifies Reasoning, Acting, and Planning" (ICML 2024, arXiv:2310.04406)
- Xu et al. — "ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models" (2023, arXiv:2305.18323)
- Qu et al. — "RISE: Recursive Introspection — Teaching Language Model Agents How to Self-Improve" (NeurIPS 2024, arXiv:2407.18219)
- Zweiger et al. — "Self-Adapting Language Models (SEAL)" (NeurIPS 2025)
- Hu et al. — "SEAL: Synergistic Co-Evolution of Agents and Learning Environments" (2026, arXiv:2605.24426)
- Wang et al. — "Voyager: An Open-Ended Embodied Agent with Large Language Models" (2023, arXiv:2305.16291)
- Shao et al. — "STORM: Synthesis of Topic Outlines through Retrieval and Multi-perspective Question Asking" (NAACL 2024)
- Zhou et al. — "Self-Challenging Language Model Agents" (NeurIPS 2025)
- Zelikman et al. — "STaR: Bootstrapping Reasoning with Reasoning" (2022)
- Robeyns et al. — "SICA: A Self-Improving Coding Agent" (2025, OpenReview)
- Du et al. / Chan et al. / Liang et al. — Multi-Agent Debate papers (2024)
- ACL 2026 Findings — "Demystifying Multi-Agent Debate: The Role of Confidence and Diversity"
- arXiv:2607.26212 — "Multi-Agent Debate Strategies: Survey, Taxonomy, and Challenges" (survey of 141 studies)
- arXiv:2608.23029 — "Meta-Moderator: Empowering Multi-Agent Debate with Meta-Cognition"

**Blog Posts & Resources:**

- Yohei Nakajima — "Better Ways to Build Self-Improving AI Agents" (yoheinakajima.com, Dec 2025)
- Agent Patterns Docs — Reflexion Agent Pattern (agent-patterns.readthedocs.io)
- Zylos Research — "AI Agent Reflection and Self-Evaluation Patterns" (Mar 2026)
- Zylos Research — "Agent Self-Correction: From Reflexion to Process Reward Models" (May 2026)
- Emergent Mind — "Reflection Agent: Self-Correcting AI"
- Appropri8 — "Reflexive AI Agents: Closing the Loop Between Perception and Self-Evaluation" (Nov 2025)
- Towards Data Science — "A Practical Guide to Memory for Autonomous LLM Agents" (Apr 2026)
- arXiv — "Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers" (arXiv:2603.07670)
- Eigent.ai — "Self-Evolved Agents: How AI Improves Itself" (Jun 2026)
- Blck Alpaca — "Multi-Agent Debate: Building Consensus Through Discussion" (Jun 2026)

**GitHub Repos:**

- Stanford-oval/storm — STORM project
- Minedojo/voyager — Voyager project
- cmu-mind/RISE — RISE implementation
- yihaohu0118/SEAL — SEAL implementation
- ScalingIntelligence/TRACE — Capability-Targeted Agentic Training
- MraDonkey/DMAD — Diverse Multi-Agent Debate

---

_Updated: September 7, 2026. This research covers all 12 patterns from the original issue with verified sources from the cited URLs._

**Archived comment 3/20** — @bacluc-agent — 2026-09-07T08:58:17Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5568076408)

**Correction to the research findings above:**

Two citation errors were identified during review and should be noted:

1. **STO venue correction:** The STO (Self-Taught Optimizer) paper by Zelikman et al. was published at **COLM 2024**, not NeurIPS 2025 as stated in section 11. The correct citation is: Zelikman et al. — "STO: Self-Taught Optimizer" (COLM 2024, arXiv:2310.02304).

2. **SEAL source clarification:** The sources section lists "Hu et al. — 'SEAL: Synergistic Co-Evolution of Agents and Learning Environments' (2026, arXiv:2605.24426)". This is a **completely different paper** that happens to share the "SEAL" acronym — it is about co-evolving agents and learning environments, NOT Self-Adapting Language Models. The SEAL section (section 6) correctly describes the Zweiger et al. paper. The Hu et al. citation should be considered a distinct, unrelated work.

Additionally, the comparison table omits Self-Challenging and STO/SICA rows — these should be added for completeness.

These are minor corrections; the core research findings remain accurate.

**Archived comment 4/20** — @BacLuc — 2026-09-07T09:38:16Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5568648208)

OK cool.

Can you find me example code where other people implemented such a thing.
Also show me the web search keywords you used, try to find other related things.
And link the resources directly that i can inspect them myself.

And propose some issues that could be implemented in this repo.

**Archived comment 5/20** — @bacluc-agent — 2026-09-07T20:45:41Z — [original](https://github.com/bacluc-agent/agent-todo/issues/76#issuecomment-5575486099)

## Verified correction and completion of the research request

This comment supersedes the earlier research comment where it conflicts with the corrections below. The original request contains 12 pattern entries; the combined “Reflection / Self-Refine” entry is intentionally split into two distinct treatments here, so both methods are explicit rather than conflated. All 12 requested entries and every named pattern are covered.

### 1. Reflection

**Treatment:** A bounded generate → evaluate/critique → revise loop. Reflection is the general evaluator-optimizer pattern: the evaluator may be the same model, another model, a test suite, or an environment. It improves an answer within one task attempt; it does not inherently provide cross-trial memory.

**Implementation:** Keep the draft, feedback, and revision as explicit state; stop on a passing external check, convergence, or a hard attempt budget. The inspectable [LangGraph reflection notebook](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/reflection/reflection.ipynb) demonstrates observe/evaluate/re-plan.

### 2. Self-Refine

**Treatment:** A specific single-model implementation of iterative refinement: generate an initial output, request self-feedback, then revise using that feedback. Unlike Reflexion, Self-Refine is not defined by persistent episodic memory across independent trials.

**Verified primary source:** [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651). The earlier link to `arXiv:2303.11366` was the Reflexion paper, not Self-Refine, and is superseded for this heading.

**Implementation lesson:** Self-feedback should be grounded in an observable evaluator where possible; use a fixed revision limit and preserve the best verified result rather than trusting “looks improved.”

### 3. Reflexion

**Treatment:** A multi-trial agent loop that stores verbal reflections as episodic memory and conditions later attempts on that memory. It differs from Reflection/Self-Refine by making cross-trial memory a defining component.

**Implementation:** actor → environment/evaluator → reflection → memory → next trial, with explicit limits and external success signals. See the [official implementation](https://github.com/noahshinn/reflexion), [LangGraph Reflexion notebook](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/reflexion/reflexion.ipynb), and [paper](https://arxiv.org/abs/2303.11366).

### 4. ReAct

**Treatment:** Interleaves reasoning, tool action, and observation on one trajectory. It optimizes the next action rather than planning a complete tree or plan upfront.

**Implementation:** a tool allowlist, structured action parser, observation history, and hard step/time/tool-call limits. See the [official code](https://github.com/ysymyth/ReAct) and [paper](https://arxiv.org/abs/2210.03629).

### 5. LATS (Language Agent Tree Search)

**Treatment:** Applies tree search to agent trajectories: select, expand, evaluate/reflect, and backpropagate. It can abandon weak branches instead of committing to one ReAct path.

**Implementation:** retain parent/child nodes, values, visits, and a bounded search budget. See the [official repository](https://github.com/lapisrocks/LanguageAgentTreeSearch), [LangGraph notebook](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/lats/lats.ipynb), and [paper](https://arxiv.org/abs/2310.04406).

### 6. REWOO (Reasoning WithOut Observation)

**Treatment:** Plans tool calls with placeholders first, executes the dependency graph, then integrates results. This trades adaptability for fewer model calls when dependencies are predictable.

**Implementation:** planner → worker/tool execution → solver with explicit placeholder substitution. See the [LangGraph notebook](https://github.com/langchain-ai/langgraph/blob/23961cff61a42b52525f3b20b4094d8d2fba1744/docs/docs/tutorials/rewoo/rewoo.ipynb), [billxbf/ReWOO](https://github.com/billxbf/ReWOO), and [paper](https://arxiv.org/abs/2305.18323).

### 7. RISE / STaR

**Treatment:** These are training-time approaches, not merely inference prompts. RISE trains recursive introspection over multi-turn correction traces; STaR bootstraps reasoning traces by generating rationales, retaining successful ones, and training on them.

**Sources:** [RISE](https://arxiv.org/abs/2407.18219) and [STaR](https://arxiv.org/abs/2203.14465). The key distinction from Reflection is weight/data updates that make correction a learned capability.

### 8. SEAL (Self-Adapting Language Models)

**Treatment:** The model generates natural-language self-edits describing data and update choices; an outer RL loop rewards edits by downstream performance while an inner training loop updates the model.

**Source:** [Self-Adapting Language Models](https://arxiv.org/abs/2506.10943). This is distinct from the similarly named SEAL co-evolution work; no reliable public implementation was found, so none is claimed here.

### 9. Voyager

**Treatment:** An embodied agent combines an automatic curriculum, executable skill library, environment feedback, and skill retrieval. Its persistent learned artifact is reusable code, not just a verbal critique.

**Sources:** [official repository](https://github.com/MineDojo/Voyager) and [paper](https://arxiv.org/abs/2305.16291).

### 10. Multi-Agent Debate (MAD)

**Treatment:** Independent agents propose, critique, revise, and reach a judged/ moderated decision. Its intended benefit is decorrelated errors; homogeneous agents can instead create an expensive echo chamber.

**Sources:** [Du et al. paper](https://arxiv.org/abs/2305.14325) and the inspectable [DMAD implementation](https://github.com/MraDonkey/DMAD). Diversity, confidence calibration, and a bounded stopping rule are the practical controls.

### 11. STORM

**Treatment:** Research synthesis is decomposed into knowledge curation, perspective-guided questions, outline generation, article writing, and polishing; Co-STORM adds collaborative multi-agent discourse.

**Sources:** [official repository](https://github.com/stanford-oval/storm), [STORM engine](https://github.com/stanford-oval/storm/blob/main/knowledge_storm/storm_wiki/engine.py), [Co-STORM engine](https://github.com/stanford-oval/storm/blob/main/knowledge_storm/collaborative_storm/engine.py), and [paper](https://arxiv.org/abs/2402.14207).

### 12. Self-Challenging Language Model Agents

**Treatment:** A challenger generates tasks with executable verification; an executor solves them; training rewards verified performance. The verification function is what prevents a self-generated curriculum from becoming unverifiable self-praise.

**Source:** [paper](https://arxiv.org/abs/2506.01716). No reliable inspectable public implementation was found in this review, so no unrelated repository is substituted.

### STO / SICA (additional named treatment in the original combined entry)

**Treatment:** STO/STOP recursively edits the agent's own code and keeps changes that improve evaluation; SICA is a separate self-improving coding-agent paper. This is source-code/policy self-modification, not verbal reflection or training on correction traces.

**Source:** [Microsoft STOP repository](https://github.com/microsoft/stop) and [STOP paper](https://arxiv.org/abs/2310.02304). I found no reliable repository for the specific SICA paper and do not present an unrelated project as SICA.

## Cross-pattern findings

The inspectable examples consistently use explicit state-machine loops, bounded budgets, evaluator/tool boundaries, and observable verification. Persistent artifacts differ: Reflexion stores verbal memory, Voyager stores executable skills, RISE/SEAL update training state, and STO/SICA update code/policy. ReAct and Reflection are inference-time control loops; RISE, STaR, and SEAL are training-time methods; LATS and MAD add structured exploration; REWOO reduces calls through upfront planning; STORM structures research synthesis.

## Proposed implementation issues

- [#120 Add a bounded evaluator loop for issue refinement](https://github.com/bacluc-agent/agent-todo/issues/120)
- [#121 Define and validate a structured issue-selector output contract](https://github.com/bacluc-agent/agent-todo/issues/121)
- [#122 Separate coordinator prompts into plan, execute, and verify phases](https://github.com/bacluc-agent/agent-todo/issues/122)
- [#123 Add structured stop reasons to issue workflows](https://github.com/bacluc-agent/agent-todo/issues/123)
- [#124 Add an optional regression harness for issue-refiner outputs](https://github.com/bacluc-agent/agent-todo/issues/124)

Issue [#76](https://github.com/bacluc-agent/agent-todo/issues/76) remains open. URLs in this corrected comment were rechecked and returned HTTP 200 on September 7, 2026.

## Web-search queries and related terms used

The following are the literal Google web-search queries used for the 12 numbered pattern entries. The terms after each query are related paper/implementation terms used to narrow interpretation and inspectable examples.

1. **Reflection**
   - Query: `Reflection LLM agent implementation evaluator optimizer LangGraph`
   - Related terms: evaluator-optimizer, generate critique revise, bounded evaluator loop, LangGraph reflection notebook.

2. **Self-Refine**
   - Query: `Self-Refine iterative refinement self-feedback implementation GitHub`
   - Related terms: iterative refinement, self-feedback, best verified result, revision limit, arXiv:2303.17651.

3. **Reflexion**
   - Query: `Reflexion agent implementation episodic memory GitHub`
   - Related terms: verbal reinforcement learning, episodic memory, actor evaluator reflector, trial loop, Noah Shinn implementation.

4. **ReAct**
   - Query: `ReAct agent official implementation tool calling GitHub`
   - Related terms: reasoning acting, thought action observation, tool allowlist, structured action parser, ysymyth/ReAct.

5. **LATS (Language Agent Tree Search)**
   - Query: `LATS Language Agent Tree Search implementation LangGraph`
   - Related terms: Monte Carlo tree search, UCT/UCB, select expand evaluate backpropagate, trajectory nodes, LanguageAgentTreeSearch.

6. **REWOO (Reasoning WithOut Observation)**
   - Query: `REWOO Reasoning Without Observation implementation LangGraph`
   - Related terms: planner worker solver, plan-execute-solve, dependency graph, placeholder substitution, billxbf/ReWOO.

7. **RISE / STaR**
   - Query: `RISE Recursive Introspection STaR self-taught reasoner implementation`
   - Related terms: recursive introspection, multi-turn correction traces, reward-weighted regression, bootstrapped rationales, self-distillation.

8. **SEAL (Self-Adapting Language Models)**
   - Query: `SEAL Self-Adapting Language Models implementation self-edit RL`
   - Related terms: natural-language self-edit, outer RL loop, inner SFT loop, downstream reward, self-generated training data.

9. **Voyager**
   - Query: `Voyager LLM agent skill library official implementation`
   - Related terms: automatic curriculum, executable skill library, code as action space, environment feedback, skill retrieval, MineDojo/Voyager.

10. **Multi-Agent Debate (MAD)**
    - Query: `Multi-Agent Debate implementation DMAD GitHub paper`
    - Related terms: proposal critique revision, moderator/judge, confidence calibration, diversity-aware debate, DMAD, echo chamber.

11. **STORM**
    - Query: `STORM multi-perspective research synthesis official implementation`
    - Related terms: knowledge curation, perspective-guided question asking, outline generation, article polishing, Co-STORM, knowledge_storm.

12. **Self-Challenging Language Model Agents**
    - Query: `Self-Challenging Language Model Agents implementation paper GitHub`
    - Related terms: challenger executor, self-generated tasks, executable verification, label-free curriculum, tool-use benchmarks.

**Additional related treatment retained from the original combined entry:** STO/SICA.

- Related terms: self-taught optimizer, STOP, recursive self-editing, source-code self-modification, self-improving coding agent, benchmark overfitting.

These searches were used to locate the papers and implementation links already cited above; no citation or existing link was replaced by this query inventory.
