# ADR-0005: BM25 sparse vectors over Postgres tsvector for hybrid retrieval

- **Status:** Accepted
- **Date:** 2026-04-27
- **Deciders:** Gabriel Morett
- **Context phase:** Phase 1C / 1D

## Context

Themis indexes Brazilian regulatory text (LGPD + ANPD resolutions and guides) for
agentic RAG. Dense embeddings (text-embedding-3-large, 3072-d) handle semantic
similarity well, but legal queries frequently key off rare exact tokens — article
numbers ("art. 41"), defined terms ("encarregado", "ANPD"), and statutory
references ("CD/ANPD nº 18/2024") that dense models tend to over-smooth.

We need a lexical channel to complement dense retrieval. Two practical options:

1. **BM25 sparse vectors stored in Qdrant** alongside the dense vectors, fused
   server-side via Qdrant's `Prefetch` + RRF / `score_boost`.
2. **Postgres `tsvector` + `ts_rank`** over the same chunks, joined on `chunk_id`
   at query time and merged client-side.

ADR-0002 already chose Qdrant as the primary vector store. The question here is
whether to keep the lexical channel inside Qdrant (BM25) or split it out to
Postgres (tsvector).

## Decision

Store BM25 sparse vectors in the same Qdrant collection as the dense vectors,
using a named-vector layout (`{"dense": ..., "sparse": ...}`). Build the BM25
encoder from the corpus at index time and query both vectors in a single round
trip.

Implementation lives in `packages/rag/sparse.py` (rank_bm25-based encoder) and
`packages/rag/index.py` (collection schema + `query_points` calls).

## Consequences

### Positive

- **Single store, single query.** No cross-system joins or two-phase retrieval —
  Qdrant returns fused top-k in one call. Latency budget for the hybrid stage is
  ~the same as a dense-only query.
- **Hybrid is first-class in Qdrant.** Sparse-vector + dense-vector hybrid is
  documented and stable since 1.10; we already track 1.17 in compose. RRF /
  score boosts are configured per-query, not per-schema.
- **No tokenizer drift between retrieval channels.** The same chunk text is fed
  to the BM25 encoder and the dense embedder; we don't have to keep a Postgres
  text-search configuration in sync with the chunker's output.
- **No extra service in the hot path.** Postgres still hosts auth/audit data
  (Phase 4+), but the retrieval critical path stays on Qdrant only.

### Negative / Trade-offs

- **BM25 corpus stats are baked at index time.** If we keep adding documents
  without rebuilding the encoder, IDF for new tokens drifts. Mitigation: the CLI
  rebuilds the encoder from scratch on `make ingest-index`, and the corpus is
  small enough (<1k docs) that a full rebuild is sub-minute.
- **Less mature tooling than Postgres FTS.** No native `to_tsquery`-style
  operators (phrase, proximity, weights). For Themis this is fine — we want
  lexical recall, not query-language expressiveness.
- **Portuguese stemming is hand-rolled.** rank_bm25 doesn't ship a PT-BR
  analyzer, so the tokenizer in `sparse.py` is a regex + lowercase pass. This is
  sufficient for legal text where the exact tokens we care about (article
  numbers, "ANPD", "encarregado") survive without stemming, but would be a
  liability for general prose.

### Neutral

- The 3072-d dense vectors dominate storage; sparse vectors add a small fraction
  on top. No meaningful disk-cost difference vs. the tsvector alternative.

## Alternatives Considered

### Option A — Postgres `tsvector` + `ts_rank`

Pros:
- Mature PT-BR text search config (`portuguese`).
- Native phrase / weighted queries.
- Ops team likely already runs Postgres.

Cons:
- Requires keeping chunks duplicated in Postgres and Qdrant, with a `chunk_id`
  join key that has to stay consistent across two ingestion paths.
- Hybrid fusion happens client-side: two queries, two latencies, app-level RRF.
- Schema drift risk between the dense and lexical channels (different
  tokenization, different chunk IDs after a re-chunk).
- Adds Postgres to the retrieval critical path before we actually need it for
  anything else.

Rejected because the operational cost (two stores, manual fusion, drift risk)
outweighs the modest expressiveness gain.

### Option B — Dense-only retrieval (no sparse channel)

Pros: simplest possible setup; just one vector type to manage.

Cons: dense models systematically under-rank exact-token queries — they
penalize "art. 41" as much as "art. 14" because the embedding doesn't preserve
discrete identifiers. For a legal-citation use case this is a known failure
mode. Dropped after early prototyping showed the encarregado smoke query
benefited materially from sparse fusion.

## References

- ADR-0002 (Qdrant over pgvector) — establishes Qdrant as the vector store.
- ADR-0004 (text-embedding-3-large) — establishes the dense channel.
- Qdrant hybrid search docs: <https://qdrant.tech/documentation/concepts/hybrid-queries/>
- rank_bm25 implementation: <https://github.com/dorianbrown/rank_bm25>
