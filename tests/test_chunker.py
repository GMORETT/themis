"""Tests for the chunker (Phase 1B).

Uses synthetic NormalizedDocuments — no fixture file needed since chunking is
pure logic over the schema models.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from core.schema import NormalizedDocument, Section
from ingestion.chunker import MAX_TOKENS, chunk_document

_BASE_DOC_KWARGS = dict(
    id="test-doc",
    source="test",
    source_url="https://example.com",
    doc_type="lei",
    title="Lei de Teste",
    jurisdiction="BR",
    enacted_at=date(2020, 1, 1),
    fetched_at=datetime.now(UTC),
)


def _doc(hierarchy: list[Section]) -> NormalizedDocument:
    return NormalizedDocument(hierarchy=hierarchy, **_BASE_DOC_KWARGS)


def _section(**kwargs: object) -> Section:
    defaults = {"artigo": "1", "text": "Texto de exemplo."}
    return Section(**{**defaults, **kwargs})  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Short article — single chunk
# ---------------------------------------------------------------------------


def test_short_article_produces_one_chunk() -> None:
    doc = _doc([_section(artigo="1", text="Art. 1º Esta é uma lei curta.")])
    chunks = chunk_document(doc)
    assert len(chunks) == 1
    assert chunks[0].article_num == "1"
    assert chunks[0].tokens_approx <= MAX_TOKENS


def test_chunk_preserves_article_num_and_title() -> None:
    doc = _doc([_section(artigo="7", text="Art. 7º Texto do artigo.")])
    chunk = chunk_document(doc)[0]
    assert chunk.article_num == "7"
    assert chunk.title == "Lei de Teste"
    assert chunk.doc_id == "test-doc"


def test_chunk_inherits_capitulo_and_secao() -> None:
    section = _section(
        artigo="1",
        capitulo="CAPÍTULO I — DISPOSIÇÕES GERAIS",
        secao="Seção I — Definições",
        text="Art. 1º Texto.",
    )
    chunk = chunk_document(_doc([section]))[0]
    assert chunk.capitulo == "CAPÍTULO I — DISPOSIÇÕES GERAIS"
    assert chunk.secao == "Seção I — Definições"


def test_paragrafo_unico_produces_single_chunk_with_para_num() -> None:
    sections = [
        _section(artigo="1", text="Art. 1º Caput do artigo."),
        _section(artigo="1", paragrafo="único", text="Parágrafo único. Disposição adicional."),
    ]
    chunks = chunk_document(_doc(sections))
    # short enough → one chunk combining both
    assert len(chunks) == 1
    assert "Parágrafo único" in chunks[0].text


# ---------------------------------------------------------------------------
# Long article — split into multiple chunks
# ---------------------------------------------------------------------------


def _long_article(n_incisos: int) -> NormalizedDocument:
    """Build an oversized article with n_incisos incisos."""
    # Each inciso carries ~50 words to force token overflow at reasonable n
    filler = "dados pessoais tratamento controlador operador encarregado finalidade " * 6
    caput = f"Art. 7º O tratamento de dados somente será permitido quando: {filler}"
    sections: list[Section] = [_section(artigo="7", text=caput)]
    for i in range(1, n_incisos + 1):
        roman = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][i - 1]
        sections.append(
            _section(artigo="7", inciso=roman, text=f"{roman} - {filler} hipótese {i};")
        )
    return _doc(sections)


def test_long_article_splits_into_multiple_chunks() -> None:
    doc = _long_article(n_incisos=10)
    chunks = chunk_document(doc)
    assert len(chunks) > 1, "oversized article should split"


def test_all_chunks_have_consistent_article_num() -> None:
    doc = _long_article(n_incisos=10)
    for chunk in chunk_document(doc):
        assert chunk.article_num == "7"


def test_no_chunk_exceeds_max_tokens_significantly() -> None:
    doc = _long_article(n_incisos=10)
    for chunk in chunk_document(doc):
        # allow small overshoot from overlap but not 2x
        assert chunk.tokens_approx < MAX_TOKENS * 2


# ---------------------------------------------------------------------------
# Multi-article document
# ---------------------------------------------------------------------------


def test_sections_without_artigo_are_skipped() -> None:
    doc = _doc([Section(text="Brasília, 14 de agosto de 2020.")])
    assert chunk_document(doc) == []


def test_multiple_articles_produce_independent_chunks() -> None:
    sections = [
        _section(artigo="1", text="Art. 1º Primeiro artigo."),
        _section(artigo="2", text="Art. 2º Segundo artigo."),
    ]
    chunks = chunk_document(_doc(sections))
    nums = [c.article_num for c in chunks]
    assert "1" in nums
    assert "2" in nums


def test_chunk_ids_are_unique() -> None:
    doc = _long_article(n_incisos=10)
    ids = [c.id for c in chunk_document(doc)]
    assert len(ids) == len(set(ids))
