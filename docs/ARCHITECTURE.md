# Architecture

> This document is a **stub**. It is polished in Phase 11 once the system is built and the design has been validated end-to-end. For the full, authoritative specification see [`SDD.md`](SDD.md).

## High-level flow (from SDD §3.1)

```
[User] → [Web UI / API Gateway]
           ↓
     [Rate Limiter + Auth]
           ↓
     [Guardrails Input Layer]      ← prompt injection, PII
           ↓
     [Query Router Agent]          ← simple | complex | out-of-scope
           ↓
     ┌─────┴──────────────────────────┐
     ↓                                ↓
[Fast Path: Haiku + Cache]    [Agentic Orchestrator (LangGraph)]
                                     ↓
                       ┌─────────────┼──────────────┬───────────┐
                       ↓             ↓              ↓           ↓
                  [Retriever   [Comparator   [Calculator   [Synthesizer
                   Agent]       Agent]        Agent]        Agent]
                       ↓            ↓             ↓            ↓
                  Vector DB     LGPD↔GDPR      Prazo ANPD   Final response
                   (Qdrant)      cross-ref      rules
                       ↓
                  [Reranker — Cross-Encoder]
                       ↓
                  [Citation Verifier]
                       ↓
     [Guardrails Output Layer]    ← citation check, refusal, PII leak
           ↓
     [Response Streaming] → User
```

## Layers

| Layer | Package | Populated in |
|-------|---------|---------------|
| HTTP / streaming | `apps/api/` | Phase 2 |
| Domain models, settings, shared utilities | `packages/core/` | Phase 1+ |
| Retrieval, reranking, generation | `packages/rag/` | Phase 2 |
| LangGraph agents, tools, state | `packages/agents/` | Phase 4 |
| Evaluation harness, metrics, dataset | `packages/evals/` | Phase 3 |
| Scrapers, chunkers, indexers | `packages/ingestion/` | Phase 1 |
| Terraform, Docker assets | `infra/` | Phase 9 |
| Next.js chat / dashboard | `apps/web/` | Phase 8 |

## Related

- [`SDD.md`](SDD.md) — full Spec-Driven Development doc (13 sections + appendices)
- [`DECISIONS.md`](DECISIONS.md) — ADR index
