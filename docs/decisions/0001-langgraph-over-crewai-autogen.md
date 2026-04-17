# ADR-0001: LangGraph as the agentic orchestration spine

- **Status:** Accepted
- **Date:** 2026-04-16
- **Deciders:** Gabriel Morett
- **Context phase:** Phase 0 (foundations), binding for Phase 4 (agentic orchestration)

## Context

Themis is a multi-agent RAG system. The SDD (§3.1, §6 Phase 4) defines a topology where a Router classifies queries, a Planner decomposes complex ones, and specialized agents (Retriever, Comparator, Calculator, Synthesizer, Critic) run in coordinated flows — sometimes sequential, sometimes parallel — with shared state, checkpoints, and per-agent timeouts.

We need an orchestration library that is the **spine** of this flow: controls the state machine, owns transitions, is observable end-to-end, and does not hide control flow behind implicit conventions. The non-functional requirements (RNF-05 observability: 100% requests traced; Fase 4 DoD: traces show clear decomposition) are first-class.

Candidate libraries evaluated: **LangGraph**, **CrewAI**, **AutoGen**.

## Decision

**Use LangGraph as the orchestration spine.** LangChain may be used for auxiliary components (loaders, splitters, retrievers, message schemas), but it is not the spine.

## Consequences

### Positive

- **Explicit state machine.** Nodes, edges, and conditional transitions are declared in code; the topology is inspectable and debuggable.
- **Native tracing hooks** via LangSmith / Langfuse callbacks — aligns with RNF-05 and Phase 7.
- **Checkpointing** is first-class, enabling replay and mid-run debugging (useful for Phase 4 DoD: "simular falha de agent").
- **Backed by LangChain team** with a Python-first API and production users — low risk of abandonment in the SDD timeline.
- **Same ecosystem as LangChain** — tool use, message types, and retrievers interoperate without adapter layers.

### Negative / Trade-offs

- **Verbosity:** declaring nodes + edges is more code than CrewAI's "give me agents and a task". We accept the verbosity as the price of explicit control.
- **Early-stage API** with occasional breaking changes. Mitigation: pin version; test suite covers flows; Phase 0 sets up the testing harness.
- **Learning curve** if we ever onboard collaborators. Mitigation: ADR + ARCHITECTURE.md + test cases serve as docs.

### Neutral

- No hard lock-in: LangGraph graphs can be reimplemented as hand-rolled state machines later if needed.

## Alternatives Considered

### Option A — CrewAI
A higher-level "agents + tasks + crew" abstraction. Fast to prototype, but control flow is largely implicit (role prompts steer behavior). Debugging a misrouted query means inspecting LLM reasoning rather than transitions. Poor fit for a system whose differentiator is **rigorous, auditable citations**.

### Option B — AutoGen (Microsoft)
Conversational multi-agent framework. Excellent for dynamic, turn-based collaboration between agents. Less suited for deterministic, DAG-shaped pipelines with fixed stages and explicit fallbacks. Also heavier on ceremony for our synchronous streaming API use case.

### Option C — Roll our own state machine
We reserve this as a future option. For Phase 4 the engineering cost outweighs the benefit, and LangGraph is already aligned with our constraints.

## References

- SDD §3.1 (architecture), §6 Phase 4 (agent topology and DoD)
- LangGraph docs: <https://langchain-ai.github.io/langgraph/>
- Planned revisit in Phase 4 if practical pain points emerge.
