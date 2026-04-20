# ADR-0003: Chunking Strategy — Hierarchical-First + 500-Token Split

**Status:** Accepted
**Date:** 2026-04-20
**Deciders:** Gabriel Morett

---

## Context

The retrieval layer (Phase 1C) needs text chunks that are:
1. **Legally coherent** — retrievable without losing the argument the article is making.
2. **Embedding-friendly** — not too long for the 8192-token context window of `text-embedding-3-large`.
3. **Metadata-rich** — every chunk must carry its article, paragraph, chapter, and section so the generator (Phase 2) can cite the exact provision.

Candidates evaluated:

| Strategy | Description | Drawback |
|---|---|---|
| **Fixed-512 sliding window** | Split every 512 tokens with 50-token overlap, regardless of structure | Splits mid-article, cuts incisos from their parent article — legally incoherent |
| **Semantic splitter** | Embed sentences, split where cosine similarity drops | High compute cost, no reproducibility, overkill for well-structured statute text |
| **Hierarchical-first** (chosen) | 1 artigo = 1 chunk; split only if > 500 tokens, at natural legal boundaries (§ → inciso → sentence) | Slightly variable chunk size; acceptable given legal structure is stable |

## Decision

**Level 1 — Article as chunk.**
Group all Sections sharing the same `artigo` into one Chunk. Legal provisions are drafted to be read as a unit; splitting an inciso from its parent article would require the retriever to reassemble context that already exists in the source.

**Level 2 — Oversized split.**
If the combined text of an article exceeds **500 tokens** (cl100k_base, same family as `text-embedding-3-large`), split at natural legal boundaries in priority order:
1. Parágrafo (`§`)
2. Inciso
3. Sentence (naive split on `.`/`;`)

Each split window carries **50-token overlap** from the previous window to preserve context at boundaries.

**500-token threshold** chosen to stay well under the 8192-token model context ceiling while keeping average chunk size meaningful (empirically: LGPD averages ~90 tokens/artigo; the longest articles are ~350 tokens — Level 2 splits are rare in this corpus).

## Consequences

- Chunk count per document depends on article structure, not a fixed grid.
- Re-chunking is cheap and deterministic (no model calls).
- If a future corpus has very long articles (e.g., annexes), Level 2 handles them automatically.
- Changing `MAX_TOKENS` requires re-embedding; kept as a named constant so the threshold is explicit.
