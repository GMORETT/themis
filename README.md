# Themis

> Agentic RAG system for Brazilian data protection law (LGPD), extensible to GDPR.
> Answers questions with **verifiable citations** or gracefully refuses when there is no documental basis.

[![CI](https://github.com/GMORETT/themis/actions/workflows/ci.yml/badge.svg)](https://github.com/GMORETT/themis/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Status:** 🚧 Phase 0 — Foundations

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
make test            # run the smoke test
```

Then visit `http://localhost:6333/dashboard` for Qdrant's UI.

The API (Phase 2+) will be served via:

```bash
uv run uvicorn apps.api.main:app --reload
```

## Roadmap

| Phase | Name | Status |
|-------|------|--------|
| 0 | Setup and Foundations | 🚧 in progress |
| 1 | Data Ingestion Pipeline | ⏳ |
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

Python 3.11 · FastAPI · LangGraph · Qdrant · Postgres · Redis · AWS Bedrock (prod) / Ollama (dev) · bge-m3 embeddings · bge-reranker-v2-m3 · RAGAS + DeepEval · Langfuse · ECS Fargate · Terraform

## Disclaimer

Themis is a portfolio project. It does **not** substitute professional legal advice.

## License

[MIT](LICENSE)
