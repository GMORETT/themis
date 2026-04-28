# Architecture Decision Records

This document indexes the ADRs for Themis. Each ADR captures one consequential decision, the alternatives we weighed, and the trade-offs we accepted.

See [`template.md`](decisions/template.md) for the structure of new ADRs.

## Index

| # | Title | Status | Phase |
|---|-------|--------|-------|
| [0001](decisions/0001-langgraph-over-crewai-autogen.md) | LangGraph as the agentic orchestration spine | Accepted | 0 (binding for 4) |
| [0002](decisions/0002-qdrant-over-pgvector.md) | Qdrant as the vector store | Accepted | 0 (binding for 1+) |
| [0003](decisions/0003-chunking-strategy.md) | Hierarchical-first chunking with 500-token split | Accepted | 1B |
| [0004](decisions/0004-embedding-model.md) | OpenAI text-embedding-3-large for dense embeddings | Accepted | 1C |
| [0005](decisions/0005-sparse-bm25-over-tsvector.md) | BM25 sparse vectors in Qdrant for hybrid retrieval | Accepted | 1C/1D |

## Conventions

- Filename: `NNNN-short-kebab-case-title.md` (4-digit zero-padded sequence).
- Statuses: **Proposed** → **Accepted** → **Deprecated** | **Superseded**.
- A **superseded** ADR links to its successor; we never rewrite history.
- Each ADR is immutable once Accepted, except to change status or append clarifying notes.
