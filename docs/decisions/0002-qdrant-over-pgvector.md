# ADR-0002: Qdrant as the vector store (over pgvector, Pinecone, Weaviate)

- **Status:** Accepted
- **Date:** 2026-04-16
- **Deciders:** Gabriel Morett
- **Context phase:** Phase 0 (foundations), binding for Phase 1 (ingestion) onward

## Context

Themis retrieval is **hybrid**: dense (bge-m3 embeddings, 1024 dims) + sparse (BM25 or sparse embedding) with reciprocal rank fusion, followed by cross-encoder reranking (bge-reranker-v2-m3). The target corpus is the LGPD + ANPD regulations + decisions + (Phase 10) GDPR — on the order of thousands of chunks, not millions.

Requirements:

- **Hybrid search first-class** (dense + sparse in one query).
- **Self-hostable for free** in dev (Docker container).
- **Free tier available in prod** for a low-traffic demo (RNF-02 cost target < $0.02/query).
- **Metadata filtering** on jurisdiction / doc_type / article_num — required for LGPD↔GDPR cross-ref (Phase 10) and for source-type filters.
- **Production-grade persistence, replication, and observability** for a portfolio demo.
- **No vendor lock-in** on proprietary APIs we can't emulate locally.

Candidates: **Qdrant**, **pgvector**, **Pinecone**, **Weaviate**.

## Decision

**Use Qdrant** as the vector store. Self-hosted via `qdrant/qdrant` Docker image in dev; Qdrant Cloud (free tier) or a small Qdrant container on ECS in prod.

## Consequences

### Positive

- **Hybrid search native:** Qdrant supports named sparse vectors alongside dense vectors in a single collection, with a single Query API covering both. No client-side fusion plumbing.
- **Rich metadata filtering** (`must`, `must_not`, range, geo, nested) without query-time performance cliffs — matches our jurisdiction + article-number filters.
- **Self-hostable trivially:** one Docker container, one port, no external dependencies.
- **Qdrant Cloud free tier** covers the demo scale.
- **Written in Rust** — predictable memory usage, relevant for sizing small prod instances.
- **Good Python client** (`qdrant-client`) with async support for our FastAPI stack.

### Negative / Trade-offs

- **Extra service to operate** (vs. pgvector's "just a Postgres extension"). We already need Postgres for conversations/audit, so we end up running two storage systems.
- **Less mature than Postgres** in terms of operational tooling (backups, point-in-time restore). Mitigation: the corpus is reproducible from `data/` + the ingestion pipeline — the vector DB is a derived artifact.
- **Another thing to learn.** Accepted — Qdrant's API is small and well-documented.

### Neutral

- We could fall back to pgvector if Qdrant becomes a pain point. The retrieval layer is abstracted in `packages/rag/` behind a thin interface (to be defined in Phase 1).

## Alternatives Considered

### Option A — pgvector (Postgres extension)
Attractive because we already need Postgres. But: hybrid search is manual client-side fusion; metadata filtering combined with ANN is not as clean; index tuning (HNSW or IVFFlat) requires care at scale. Best fit when the corpus is tiny and you want zero extra services. Reasonable fallback, not first choice.

### Option B — Pinecone (managed)
Best developer experience but **paid only** (no free tier sufficient for a demo left running). Introduces vendor lock-in (proprietary APIs). Violates RNF-07 (reproducibility from a clean machine in < 15 min without external accounts).

### Option C — Weaviate
Capable hybrid search, but heavier resource footprint and a more opinionated schema model (class/property). Overkill for our scale and adds friction for contributors.

## References

- SDD §3.2 (components), §4.3 (storage), §6 Phase 1 (chunking + indexing)
- Qdrant hybrid search docs: <https://qdrant.tech/documentation/concepts/hybrid-queries/>
- Planned benchmark note in Phase 1 ADR if real-world ingestion reveals pain points.
