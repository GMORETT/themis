"""Themis API entrypoint. Placeholder until Phase 2 wires up the RAG baseline."""

from fastapi import FastAPI

app = FastAPI(
    title="Themis",
    description="Agentic RAG system for LGPD/GDPR.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "phase": "0"}
