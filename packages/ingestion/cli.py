"""Typer CLI for the Themis ingestion pipeline.

Entry point for the `make ingest-*` targets and for manual runs. Each subcommand
is idempotent and safe to re-run.

Run via: `uv run python -m ingestion.cli <command>`
"""

from __future__ import annotations

from pathlib import Path

import typer

from ingestion import normalize
from ingestion.chunker import chunk_document
from ingestion.sources import planalto

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = REPO_ROOT / "data" / "raw"
DATA_PROCESSED_V1 = REPO_ROOT / "data" / "processed" / "v1"

app = typer.Typer(help="Themis ingestion pipeline.", no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Themis ingestion pipeline — subcommands below."""


@app.command("fetch-lgpd")
def fetch_lgpd() -> None:
    """Fetch LGPD from Planalto, parse, and write normalized JSONL."""
    raw_path = DATA_RAW / "planalto" / "lgpd-13709-2018.html"
    jsonl_path = DATA_PROCESSED_V1 / "lgpd.jsonl"

    typer.echo(f"→ fetch raw HTML → {raw_path}")
    raw = planalto.fetch_raw(raw_path)
    typer.echo(f"  {len(raw):,} bytes")

    typer.echo("→ parse + normalize")
    doc = planalto.parse_lgpd(raw)
    articles = [s for s in doc.hierarchy if s.artigo and not s.paragrafo and not s.inciso]
    typer.echo(f"  {len(articles)} artigos, {len(doc.hierarchy)} sections total")

    typer.echo(f"→ write JSONL → {jsonl_path}")
    n = normalize.write_jsonl([doc], jsonl_path)
    typer.echo(f"✓ wrote {n} document(s)")


@app.command("chunk")
def chunk() -> None:
    """Chunk normalized LGPD JSONL into retrieval units."""
    jsonl_path = DATA_PROCESSED_V1 / "lgpd.jsonl"
    chunks_path = DATA_PROCESSED_V1 / "chunks.jsonl"

    typer.echo(f"→ read {jsonl_path}")
    docs = normalize.read_jsonl(jsonl_path)
    typer.echo(f"  {len(docs)} document(s)")

    all_chunks = []
    for doc in docs:
        doc_chunks = chunk_document(doc)
        all_chunks.extend(doc_chunks)

    avg_tok = sum(c.tokens_approx for c in all_chunks) / len(all_chunks) if all_chunks else 0
    max_tok = max((c.tokens_approx for c in all_chunks), default=0)
    typer.echo(f"  {len(all_chunks)} chunks | avg {avg_tok:.0f} tok | max {max_tok} tok")

    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    with chunks_path.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(c.model_dump_json())
            f.write("\n")
    typer.echo(f"✓ wrote {len(all_chunks)} chunks → {chunks_path}")


if __name__ == "__main__":
    app()
