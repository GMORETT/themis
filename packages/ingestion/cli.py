"""Typer CLI for the Themis ingestion pipeline.

Entry point for the `make ingest-*` targets and for manual runs. Each subcommand
is idempotent and safe to re-run.

Run via: `uv run python -m ingestion.cli <command>`
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rag.embedder import DIMENSIONS, MODEL, OpenAIEmbedder
from rag.index import COLLECTION, ensure_collection, upsert_chunks
from rag.sparse import BM25Encoder

from ingestion import normalize
from ingestion.chunker import chunk_document
from ingestion.sources import anpd, planalto

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


@app.command("embed")
def embed(
    rebuild: bool = typer.Option(False, "--rebuild", help="Re-embed even if vectors file exists."),
) -> None:
    """Embed chunks via OpenAI and write vectors JSONL."""
    chunks_path = DATA_PROCESSED_V1 / "chunks.jsonl"
    vectors_path = DATA_PROCESSED_V1 / "vectors.jsonl"

    if vectors_path.exists() and not rebuild:
        typer.echo(f"✓ vectors already exist at {vectors_path} (use --rebuild to re-embed)")
        return

    typer.echo(f"→ read {chunks_path}")
    chunks = []
    with chunks_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                from core.schema import Chunk

                chunks.append(Chunk.model_validate_json(line))
    typer.echo(f"  {len(chunks)} chunks")

    embedder = OpenAIEmbedder()
    typer.echo(f"→ embed via {MODEL} ({DIMENSIONS}-d) in batches of 100")
    texts = [c.text for c in chunks]
    vectors, total_tokens = embedder.embed_with_usage(texts)
    cost = total_tokens * 0.13 / 1_000_000
    typer.echo(f"  {total_tokens:,} tokens consumed | estimated cost ${cost:.5f}")

    vectors_path.parent.mkdir(parents=True, exist_ok=True)
    with vectors_path.open("w", encoding="utf-8") as f:
        for chunk, vec in zip(chunks, vectors, strict=True):
            f.write(json.dumps({"id": chunk.id, "vector": vec}))
            f.write("\n")
    typer.echo(f"✓ wrote {len(vectors)} vectors → {vectors_path}")


@app.command("index")
def index(
    rebuild: bool = typer.Option(False, "--rebuild", help="Delete and recreate Qdrant collection."),
) -> None:
    """Index embedded chunks into Qdrant."""

    from rag.index import _get_client

    chunks_path = DATA_PROCESSED_V1 / "chunks.jsonl"
    vectors_path = DATA_PROCESSED_V1 / "vectors.jsonl"

    typer.echo("→ read chunks + vectors")
    chunks = []
    with chunks_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                from core.schema import Chunk

                chunks.append(Chunk.model_validate_json(line))

    vectors: list[list[float]] = []
    with vectors_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                vectors.append(json.loads(line)["vector"])

    typer.echo(f"  {len(chunks)} chunks, {len(vectors)} vectors")

    typer.echo("→ build BM25 encoder")
    encoder = BM25Encoder([c.text for c in chunks])

    client = _get_client()
    typer.echo(f"→ ensure collection '{COLLECTION}' (rebuild={rebuild})")
    ensure_collection(client, rebuild=rebuild)

    typer.echo("→ upsert to Qdrant")
    n = upsert_chunks(client, chunks, vectors, encoder)
    info = client.get_collection(COLLECTION)
    typer.echo(f"✓ indexed {n} points | collection has {info.points_count} points total")


@app.command("fetch-anpd")
def fetch_anpd_cmd() -> None:
    """Fetch ANPD resolutions + guides, chunk, and append to JSONL."""
    raw_resolucoes = DATA_RAW / "anpd" / "resolucoes"
    raw_guias = DATA_RAW / "anpd" / "guias"
    jsonl_resolucoes = DATA_PROCESSED_V1 / "anpd_resolucoes.jsonl"
    jsonl_guias = DATA_PROCESSED_V1 / "anpd_guias.jsonl"
    chunks_path = DATA_PROCESSED_V1 / "chunks.jsonl"

    typer.echo("→ fetch resoluções CD/ANPD")
    resolucoes = anpd.fetch_resolucoes(raw_resolucoes)
    typer.echo(f"  {len(resolucoes)} resoluções fetched")
    normalize.write_jsonl(resolucoes, jsonl_resolucoes)

    typer.echo("→ fetch guias ANPD")
    guias = anpd.fetch_guias(raw_guias)
    typer.echo(f"  {len(guias)} guias fetched")
    normalize.write_jsonl(guias, jsonl_guias)

    all_docs = resolucoes + guias
    typer.echo(f"→ chunk {len(all_docs)} ANPD documents")
    anpd_chunks = []
    for doc in all_docs:
        anpd_chunks.extend(chunk_document(doc))
    typer.echo(f"  {len(anpd_chunks)} chunks produced")

    # Idempotent rewrite: keep non-ANPD chunks (LGPD), replace ANPD section.
    kept: list[str] = []
    if chunks_path.exists():
        for line in chunks_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            if '"source":"anpd"' in line or '"source": "anpd"' in line:
                continue
            kept.append(line)

    with chunks_path.open("w", encoding="utf-8") as f:
        for line in kept:
            f.write(line)
            f.write("\n")
        for c in anpd_chunks:
            f.write(c.model_dump_json())
            f.write("\n")
    typer.echo(
        f"✓ wrote {len(kept)} kept + {len(anpd_chunks)} ANPD = "
        f"{len(kept) + len(anpd_chunks)} chunks → {chunks_path}"
    )


if __name__ == "__main__":
    app()
