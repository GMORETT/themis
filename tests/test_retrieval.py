"""Tests for HybridRetriever.

The Qdrant client and OpenAI embedder are mocked — these tests exercise the
retrieval glue (right Qdrant call shape, right fallback behaviour, payload
shape) without hitting any network.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from qdrant_client import models
from rag.embedder import Embedder
from rag.retrieval import HybridRetriever
from rag.sparse import BM25Encoder

CORPUS = [
    "Art. 41. O controlador deverá indicar encarregado pelo tratamento de dados pessoais.",
    "Resolução CD/ANPD nº 18 — Regulamento sobre a atuação do encarregado.",
    "Art. 7. O tratamento de dados pessoais somente poderá ser realizado nas seguintes hipóteses.",
]


class _StubEmbedder(Embedder):
    """Returns a fixed vector regardless of input — we only check shape/usage."""

    def __init__(self, dim: int = 8) -> None:
        self._vec = [0.1] * dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec for _ in texts]


def _qdrant_mock_with_results(payloads: list[dict[str, object]]) -> MagicMock:
    points = [SimpleNamespace(score=1.0 - i * 0.1, payload=p) for i, p in enumerate(payloads)]
    client = MagicMock()
    client.query_points.return_value = SimpleNamespace(points=points)
    return client


@pytest.fixture
def retriever() -> HybridRetriever:
    return HybridRetriever(
        encoder=BM25Encoder(CORPUS),
        embedder=_StubEmbedder(),
        client=_qdrant_mock_with_results(
            [
                {"article_num": "41", "text": "...", "source": "planalto"},
                {"article_num": "7", "text": "...", "source": "planalto"},
            ]
        ),
    )


def test_retrieve_returns_payload_with_score(retriever: HybridRetriever) -> None:
    results = retriever.retrieve("encarregado", top_k=2)
    assert len(results) == 2
    assert results[0]["article_num"] == "41"
    assert results[0]["score"] == pytest.approx(1.0)
    assert results[1]["score"] == pytest.approx(0.9)


def test_retrieve_uses_hybrid_when_query_has_known_terms(retriever: HybridRetriever) -> None:
    retriever.retrieve("encarregado", top_k=5)
    call = retriever._client.query_points.call_args  # type: ignore[attr-defined]
    kwargs = call.kwargs
    assert "prefetch" in kwargs, "hybrid path should use prefetch (dense + sparse)"
    assert len(kwargs["prefetch"]) == 2
    assert kwargs["prefetch"][0].using == "dense"
    assert kwargs["prefetch"][1].using == "sparse"
    assert isinstance(kwargs["query"], models.FusionQuery)
    assert kwargs["query"].fusion == models.Fusion.RRF


def test_retrieve_falls_back_to_dense_when_no_bm25_overlap() -> None:
    retriever = HybridRetriever(
        encoder=BM25Encoder(CORPUS),
        embedder=_StubEmbedder(),
        client=_qdrant_mock_with_results([{"article_num": "1"}]),
    )
    # "xyzzy" — no token in the BM25 vocabulary.
    retriever.retrieve("xyzzy plover", top_k=3)
    call = retriever._client.query_points.call_args  # type: ignore[attr-defined]
    kwargs = call.kwargs
    assert "prefetch" not in kwargs, "no-overlap query must skip hybrid prefetch"
    assert kwargs["using"] == "dense"
    assert kwargs["limit"] == 3


def test_from_chunks_jsonl_builds_encoder_from_file(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        "\n".join(json.dumps({"text": text, "id": str(i)}) for i, text in enumerate(CORPUS)),
        encoding="utf-8",
    )
    retriever = HybridRetriever.from_chunks_jsonl(
        chunks_path,
        embedder=_StubEmbedder(),
        client=_qdrant_mock_with_results([]),
    )
    # Vocab should contain a known LGPD term from the fixture corpus.
    assert "encarregado" in retriever._bm25._vocab  # type: ignore[attr-defined]


def test_top_k_is_passed_through(retriever: HybridRetriever) -> None:
    retriever.retrieve("dados pessoais", top_k=7, prefetch_k=42)
    call = retriever._client.query_points.call_args  # type: ignore[attr-defined]
    assert call.kwargs["limit"] == 7
    assert call.kwargs["prefetch"][0].limit == 42
    assert call.kwargs["prefetch"][1].limit == 42


def test_source_filter_propagates_to_both_prefetches(retriever: HybridRetriever) -> None:
    retriever.retrieve("encarregado", top_k=3, source="planalto")
    call = retriever._client.query_points.call_args  # type: ignore[attr-defined]
    for prefetch in call.kwargs["prefetch"]:
        assert prefetch.filter is not None
        condition = prefetch.filter.must[0]
        assert condition.key == "source"
        assert condition.match.value == "planalto"


def test_source_filter_propagates_to_dense_only_fallback() -> None:
    retriever = HybridRetriever(
        encoder=BM25Encoder(CORPUS),
        embedder=_StubEmbedder(),
        client=_qdrant_mock_with_results([]),
    )
    retriever.retrieve("xyzzy plover", top_k=3, source="anpd")
    call = retriever._client.query_points.call_args  # type: ignore[attr-defined]
    qfilter = call.kwargs["query_filter"]
    assert qfilter is not None
    assert qfilter.must[0].match.value == "anpd"


def test_no_source_filter_omits_filter_field(retriever: HybridRetriever) -> None:
    retriever.retrieve("encarregado", top_k=3)
    call = retriever._client.query_points.call_args  # type: ignore[attr-defined]
    for prefetch in call.kwargs["prefetch"]:
        assert prefetch.filter is None
