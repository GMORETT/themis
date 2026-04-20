# ADR-0004: Embedding Model — OpenAI text-embedding-3-large

**Status:** Accepted
**Date:** 2026-04-20
**Deciders:** Gabriel Morett

---

## Context

The RAG pipeline requires a dense embedding model for semantic retrieval. Evaluated:

| Model | Dims | MTEB (avg) | Cost / 1M tok | Operation |
|---|---|---|---|---|
| **OpenAI text-embedding-3-large** | 3072 | ~64.6 | $0.13 | API call |
| BAAI/bge-m3 | 1024 | ~62.7 | $0 | Local GPU/CPU |
| Voyage 3-large | 1024 | ~67.1 | $0.18 | API call |
| AWS Bedrock Titan Text v2 | 1024 | ~61.2 | $0.02 | API call |

## Decision

**OpenAI `text-embedding-3-large` (3072-d native).**

Rationale:
1. **Quality**: Top-tier MTEB score with multilingual support; bge-m3 requires local GPU for reasonable throughput.
2. **Cost negligible**: Full corpus (~250k tokens) costs ~$0.03. Re-embedding if we switch models: also ~$0.03.
3. **Zero ops**: No model weights to download or serve; no torch dependency.
4. **Interface abstracted**: `Embedder` ABC in `rag/embedder.py` lets us swap to bge-m3/Voyage in Phase 3 after building a golden evaluation set.

## Consequences

- Corpus is tied to OpenAI's embedding space. Changing models requires full re-indexing (~$0.03, ~2 min).
- `OPENAI_API_KEY` required at embed time; CI tests use mocks and never call the API.
- Cost guard (`$1.00` hard stop) prevents runaway spend on misconfigured loops.
- Collection versioned as `themis_lgpd_v1` — any model change creates `v2`, not in-place mutation.
