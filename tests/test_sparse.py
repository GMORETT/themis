"""Tests for the BM25 sparse encoder.

The encoder is asymmetric by design — `encode_document` produces TF, `encode`
produces IDF-weighted query terms. These tests pin both sides plus the vocab
behaviour the index relies on.
"""

from __future__ import annotations

from rag.sparse import BM25Encoder, _tokenize

CORPUS = [
    "Art. 41. O controlador deverá indicar encarregado pelo tratamento de dados pessoais.",
    "O encarregado é a pessoa indicada pelo controlador para atuar como canal de comunicação.",
    "A ANPD comunica decisões e regulamentações sobre proteção de dados pessoais.",
    "Resolução nº 18 trata da atuação do encarregado pelo tratamento.",
]


def test_tokenize_handles_portuguese_diacritics() -> None:
    tokens = _tokenize("Atuação do encarregado — proteção de dados pessoais.")
    assert "atuação" in tokens
    assert "encarregado" in tokens
    assert "proteção" in tokens
    assert "—" not in tokens


def test_encode_returns_idf_weighted_query_terms() -> None:
    encoder = BM25Encoder(CORPUS)
    sparse = encoder.encode("encarregado")
    assert len(sparse) == 1
    weight = next(iter(sparse.values()))
    assert weight > 0


def test_encode_assigns_higher_idf_to_rarer_terms() -> None:
    encoder = BM25Encoder(CORPUS)
    rare = encoder.encode("anpd")
    common = encoder.encode("encarregado")
    rare_w = next(iter(rare.values()))
    common_w = next(iter(common.values()))
    # "anpd" appears in 1 doc, "encarregado" in 3 → ANPD must score strictly higher.
    assert rare_w > common_w


def test_encode_skips_unknown_tokens() -> None:
    encoder = BM25Encoder(CORPUS)
    assert encoder.encode("xyzzy plover frobnicate") == {}


def test_encode_aggregates_repeated_query_tokens() -> None:
    encoder = BM25Encoder(CORPUS)
    single = encoder.encode("encarregado")
    repeated = encoder.encode("encarregado encarregado encarregado")
    single_w = next(iter(single.values()))
    repeated_w = next(iter(repeated.values()))
    assert repeated_w == 3 * single_w


def test_encode_document_returns_term_frequencies() -> None:
    encoder = BM25Encoder(CORPUS)
    tf = encoder.encode_document("encarregado encarregado dados")
    # Three known tokens, "encarregado" twice.
    assert sum(tf.values()) == 3
    encarregado_idx = encoder._vocab["encarregado"]  # type: ignore[attr-defined]
    assert tf[encarregado_idx] == 2.0


def test_encode_document_extends_vocab_for_unseen_tokens() -> None:
    encoder = BM25Encoder(CORPUS)
    initial_size = len(encoder._vocab)  # type: ignore[attr-defined]
    encoder.encode_document("nóvotermo")
    assert "nóvotermo" in encoder._vocab  # type: ignore[attr-defined]
    assert len(encoder._vocab) == initial_size + 1  # type: ignore[attr-defined]


def test_encode_query_does_not_extend_vocab() -> None:
    encoder = BM25Encoder(CORPUS)
    initial_size = len(encoder._vocab)  # type: ignore[attr-defined]
    encoder.encode("nóvotermo encarregado")
    assert len(encoder._vocab) == initial_size  # type: ignore[attr-defined]
