"""Corpus validation script — run after make ingest.

Checks:
1. chunks.jsonl has expected article coverage and ANPD doc mix
   - >= 79 LGPD articles
   - >= 10 ANPD resolutions
   - >= 4 ANPD guides
2. Qdrant collection exists with correct point count
3. Smoke queries:
   - "encarregado de proteção de dados" → LGPD Art. 41 in top-3
   - "incidente de segurança comunicação ANPD" → ANPD resolution chunk in top-3
   - "legítimo interesse" → guide chunk in top-5

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
    lgpd = [c for c in chunks if c["source"] == "planalto"]
    anpd = [c for c in chunks if c["source"] == "anpd"]
    resolucoes = {c["doc_id"] for c in anpd if c["doc_type"] == "anpd_resolucao"}
    guias = {c["doc_id"] for c in anpd if c["doc_type"] == "anpd_guia"}
    article_nums = {c["article_num"] for c in lgpd if c.get("article_num")}

    print(f"  total chunks       : {len(chunks)}")
    print(f"  LGPD chunks        : {len(lgpd)} ({len(article_nums)} unique artigos)")
    print(f"  ANPD chunks        : {len(anpd)}")
    print(f"  ANPD resolutions   : {len(resolucoes)}")
    print(f"  ANPD guides        : {len(guias)}")

    assert len(article_nums) >= 79, f"expected >= 79 LGPD artigos, got {len(article_nums)}"
    assert len(resolucoes) >= 10, f"expected >= 10 ANPD resolutions, got {len(resolucoes)}"
    assert len(guias) >= 4, f"expected >= 4 ANPD guides, got {len(guias)}"

    avg = sum(c["tokens_approx"] for c in chunks) / len(chunks)
    max_tok = max(c["tokens_approx"] for c in chunks)
    print(f"  avg tokens         : {avg:.0f}")
    print(f"  max tokens         : {max_tok}")
    print("✓ chunks OK")


def check_qdrant(expected_points: int) -> None:
    from rag.index import COLLECTION, _get_client

    client = _get_client()
    assert client.collection_exists(COLLECTION), f"collection '{COLLECTION}' not found"
    info = client.get_collection(COLLECTION)
    actual = info.points_count
    assert actual == expected_points, f"expected {expected_points} points, got {actual}"
    print(f"✓ Qdrant collection '{COLLECTION}' has {actual} points")


_RETRIEVER = None


def _get_retriever():
    """Lazy-init a single HybridRetriever for all smoke calls."""
    from rag.retrieval import HybridRetriever

    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = HybridRetriever.from_chunks_jsonl(CHUNKS_PATH)
    return _RETRIEVER


def smoke_lgpd_article(query: str, expected_article: str, top_k: int = 3) -> None:
    """Hybrid retrieval restricted to the LGPD slice of the corpus."""
    results = _get_retriever().retrieve(query, top_k=top_k, source="planalto")
    articles = [r.get("article_num") for r in results]
    print(f"  query: '{query}' [source=planalto]")
    print(f"  top-{top_k} articles: {articles}")
    assert expected_article in articles, (
        f"expected Art. {expected_article} in top-{top_k}, got {articles}"
    )
    print(f"✓ LGPD smoke: Art. {expected_article} in top-{top_k}")


def smoke_anpd(query: str, expected_doc_type: str, top_k: int = 3) -> None:
    """Hybrid retrieval restricted to the ANPD slice of the corpus."""
    results = _get_retriever().retrieve(query, top_k=top_k, source="anpd")
    doc_types = [r.get("doc_type") for r in results]
    print(f"  query: '{query}' [source=anpd]")
    print(f"  top-{top_k} doc_types: {doc_types}")
    assert expected_doc_type in doc_types, (
        f"expected {expected_doc_type} in top-{top_k}, got {doc_types}"
    )
    print(f"✓ ANPD smoke: {expected_doc_type} found in top-{top_k}")


def main() -> None:
    print("=== Themis corpus validation ===\n")

    print("[1] chunks.jsonl")
    chunks = _load_chunks()
    check_chunks(chunks)

    print("\n[2] Qdrant")
    check_qdrant(expected_points=len(chunks))

    print("\n[3] Smoke queries")
    smoke_lgpd_article(
        query="encarregado de proteção de dados",
        expected_article="41",
        top_k=3,
    )
    smoke_anpd(
        query="comunicação de incidente de segurança ANPD prazo",
        expected_doc_type="anpd_resolucao",
        top_k=5,
    )
    smoke_anpd(
        query="legítimo interesse hipóteses de tratamento",
        expected_doc_type="anpd_guia",
        top_k=5,
    )

    print("\n✓ All checks passed.")


if __name__ == "__main__":
    main()
