"""Corpus validation script — run after make ingest.

Checks:
1. chunks.jsonl has expected article coverage (79 artigos LGPD)
2. Qdrant collection exists with correct point count
3. Smoke query: "encarregado de proteção de dados" → Art. 41 in top-3

Usage:
    PYTHONPATH=apps:packages uv run python scripts/validate_corpus.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_PATH = REPO_ROOT / "data" / "processed" / "v1" / "chunks.jsonl"
VECTORS_PATH = REPO_ROOT / "data" / "processed" / "v1" / "vectors.jsonl"

# Add packages to path when running directly
sys.path.insert(0, str(REPO_ROOT / "packages"))
sys.path.insert(0, str(REPO_ROOT / "apps"))


def _load_chunks() -> list[dict]:
    with CHUNKS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _load_vectors() -> list[list[float]]:
    with VECTORS_PATH.open(encoding="utf-8") as f:
        return [json.loads(line)["vector"] for line in f if line.strip()]


def check_chunks(chunks: list[dict]) -> None:
    article_nums = {c["article_num"] for c in chunks if c.get("article_num")}
    print(f"  total chunks : {len(chunks)}")
    print(f"  unique artigos: {len(article_nums)}")
    assert len(article_nums) >= 79, f"expected >= 79 artigos, got {len(article_nums)}"
    avg = sum(c["tokens_approx"] for c in chunks) / len(chunks)
    max_tok = max(c["tokens_approx"] for c in chunks)
    print(f"  avg tokens   : {avg:.0f}")
    print(f"  max tokens   : {max_tok}")
    print("✓ chunks OK")


def check_qdrant(expected_points: int) -> None:
    from rag.index import COLLECTION, _get_client

    client = _get_client()
    assert client.collection_exists(COLLECTION), f"collection '{COLLECTION}' not found"
    info = client.get_collection(COLLECTION)
    actual = info.points_count
    assert actual == expected_points, f"expected {expected_points} points, got {actual}"
    print(f"✓ Qdrant collection '{COLLECTION}' has {actual} points")


def smoke_query(query: str, expected_article: str, top_k: int = 3) -> None:
    from rag.embedder import OpenAIEmbedder
    from rag.index import _get_client, search

    client = _get_client()
    embedder = OpenAIEmbedder()
    vec = embedder.embed([query])[0]
    results = search(client, vec, top_k=top_k)
    articles = [r.get("article_num") for r in results]
    print(f"  query: '{query}'")
    print(f"  top-{top_k} articles: {articles}")
    assert expected_article in articles, (
        f"expected Art. {expected_article} in top-{top_k}, got {articles}"
    )
    print(f"✓ smoke query: Art. {expected_article} in top-{top_k}")


def main() -> None:
    print("=== Themis corpus validation ===\n")

    print("[1] chunks.jsonl")
    chunks = _load_chunks()
    check_chunks(chunks)

    print("\n[2] Qdrant")
    check_qdrant(expected_points=len(chunks))

    print("\n[3] Smoke query")
    smoke_query(
        query="encarregado de proteção de dados",
        expected_article="41",
        top_k=3,
    )

    print("\n✓ All checks passed.")


if __name__ == "__main__":
    main()
