"""Tests for the OpenAI embedder — uses mocks, never calls the real API."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from rag.embedder import DIMENSIONS, OpenAIEmbedder


def _make_embedder() -> OpenAIEmbedder:
    with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}):
        return OpenAIEmbedder()


def _fake_response(**kwargs: object) -> MagicMock:
    texts = kwargs.get("input", [])
    response = MagicMock()
    response.data = [MagicMock(embedding=[0.0] * DIMENSIONS) for _ in texts]
    response.usage.total_tokens = sum(len(str(t).split()) for t in texts)  # type: ignore[union-attr]
    return response


def test_embed_returns_correct_dimension() -> None:
    embedder = _make_embedder()
    with patch.object(embedder._client.embeddings, "create", side_effect=_fake_response):
        vecs = embedder.embed(["texto curto de teste"])
    assert len(vecs) == 1
    assert len(vecs[0]) == DIMENSIONS


def test_embed_returns_one_vector_per_text() -> None:
    embedder = _make_embedder()
    texts = ["texto um", "texto dois", "texto três"]
    with patch.object(embedder._client.embeddings, "create", side_effect=_fake_response):
        vecs = embedder.embed(texts)
    assert len(vecs) == len(texts)


def test_cost_guard_raises_before_api_call() -> None:
    embedder = _make_embedder()
    # 1 token ≈ 4 chars; need > 1.0 / (0.13/1_000_000) ≈ 7.7M tokens → > 31M chars
    huge_text = "a" * 40_000_000
    with pytest.raises(RuntimeError, match="hard stop"):
        embedder.embed([huge_text])


def test_embed_with_usage_returns_token_count() -> None:
    embedder = _make_embedder()
    texts = ["encarregado de proteção de dados pessoais"]
    with patch.object(embedder._client.embeddings, "create", side_effect=_fake_response):
        vecs, tokens = embedder.embed_with_usage(texts)
    assert tokens > 0
    assert len(vecs) == 1
