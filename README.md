# Themis

> Agentic RAG system for Brazilian data protection law (LGPD), extensible to GDPR.
> Answers questions with **verifiable citations** or gracefully refuses when there is no documental basis.

[![CI](https://github.com/GMORETT/themis/actions/workflows/ci.yml/badge.svg)](https://github.com/GMORETT/themis/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Status:** 🚧 Phase 1 — Data Ingestion Pipeline (1A–1D complete: LGPD + ANPD corpus indexed) · tracking progress in [`docs/SDD.md`](docs/SDD.md)

---

## Why

LGPD/GDPR questions sent to a raw LLM come back without citations, prone to hallucination, with no audit trail. That is unacceptable in a regulatory context.

Themis answers with:

- **Mandatory, verifiable citations** from primary sources (articles, ANPD regulations, administrative decisions)
- **Agentic decomposition** of complex queries across specialized agents (Router → Planner → Retriever / Comparator / Calculator / Synthesizer / Critic)
- **Graceful refusal** when there is no documental basis
- **Cross-jurisdictional comparison** LGPD ↔ GDPR
- **Full audit trail** with cost and latency observability

## Quick start (dev)

Requires: WSL2 (or Linux/macOS), Docker, and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/GMORETT/themis.git
cd themis
uv sync              # install Python deps
docker compose up -d # start postgres, redis, qdrant
cp .env.example .env # add OPENAI_API_KEY
make test            # run the smoke test
```

Then visit `http://localhost:6333/dashboard` for Qdrant's UI.

The API (Phase 2+) will be served via:

```bash
uv run uvicorn apps.api.main:app --reload
```

## Ingestion pipeline (Phase 1)

Build the LGPD + ANPD corpus end-to-end:

```bash
make ingest          # runs the full pipeline (see sub-targets below)
```

Or step by step:

| Target | What it does |
|--------|--------------|
| `make ingest-lgpd`  | Scrape LGPD (Lei nº 13.709/2018) from Planalto and write `data/processed/v1/lgpd.jsonl`. |
| `make ingest-chunk` | Chunk LGPD into ~500-token retrieval units (one per artigo, hierarchical-first split). |
| `make ingest-anpd`  | Scrape CD/ANPD resolutions + official guides; chunk and merge into `chunks.jsonl`. |
| `make ingest-index` | Embed chunks via `text-embedding-3-large` and index into Qdrant (`themis_lgpd_v1`). |

After indexing, validate the corpus:

```bash
PYTHONPATH=apps:packages uv run python scripts/validate_corpus.py
```

This checks chunk coverage (≥79 LGPD articles, ≥10 ANPD resolutions, ≥4 guides),
Qdrant point counts, and runs three smoke queries (LGPD article retrieval, ANPD
resolution retrieval, guide retrieval).

**Cost guardrail:** the OpenAI embedder hard-stops if a single batch's estimated
cost exceeds `COST_HARD_STOP_USD = $1`. The full Phase 1 corpus embeds for
~$0.02 total.

## Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 0 | Setup and Foundations | ✅ done |
| 1 | Data Ingestion Pipeline | 🚧 1A/1B/1C/1D complete |
| 2 | RAG Baseline (non-agentic) | ⏳ |
| 3 | Evaluation Framework | ⏳ |
| 4 | Agentic Orchestration | ⏳ |
| 5 | Optimization (cost/latency) | ⏳ |
| 6 | Guardrails and Security | ⏳ |
| 7 | Observability | ⏳ |
| 8 | Frontend | ⏳ |
| 9 | Deploy on AWS | ⏳ |
| 10 | GDPR Extension | ⏳ |
| 11 | Documentation Polish | ⏳ |

## Documentation

- [`docs/SDD.md`](docs/SDD.md) — full Spec-Driven Development document
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — architecture overview
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — index of Architecture Decision Records

## Tech stack (summary)

Python 3.11 · FastAPI · LangGraph · Qdrant (dense + sparse BM25) · Postgres · Redis · AWS Bedrock (prod) / Ollama (dev) · OpenAI text-embedding-3-large (dev) → bge-m3 (target) · bge-reranker-v2-m3 · RAGAS + DeepEval · Langfuse · ECS Fargate · Terraform

## Disclaimer

Themis is a portfolio project. It does **not** substitute professional legal advice.

## License

[MIT](LICENSE)
