"""Tests for the Planalto LGPD parser.

Uses the checked-in `tests/fixtures/planalto-lgpd-sample.html` to exercise the
parser offline. The real LGPD page is parsed in the validation script, not here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ingestion.sources.planalto import parse_lgpd

FIXTURE = Path(__file__).parent / "fixtures" / "planalto-lgpd-sample.html"


@pytest.fixture(scope="module")
def parsed():
    return parse_lgpd(FIXTURE.read_bytes())


def test_parser_returns_expected_metadata(parsed) -> None:
    assert parsed.id == "lgpd-13709-2018"
    assert parsed.source == "planalto"
    assert parsed.doc_type == "lei"
    assert parsed.jurisdiction == "BR"
    assert parsed.title.startswith("Lei Geral de Proteção de Dados")


def test_parser_extracts_each_current_article_once(parsed) -> None:
    article_nums = [
        s.artigo for s in parsed.hierarchy if s.artigo and not s.paragrafo and not s.inciso
    ]
    assert article_nums == ["1", "7", "20", "56", "55-A", "62"]


def test_revoked_versions_are_skipped(parsed) -> None:
    all_text = " ".join(s.text for s in parsed.hierarchy)
    assert "Texto original revogado" not in all_text
    assert "Versão antiga revogada" not in all_text
    assert "O titular dos dados tem direito a solicitar a revisão" in all_text


def test_hierarchy_is_attached_to_article(parsed) -> None:
    art7 = next(s for s in parsed.hierarchy if s.artigo == "7" and not s.paragrafo and not s.inciso)
    assert art7.capitulo is not None
    assert "CAPÍTULO II" in art7.capitulo
    assert art7.secao is not None
    assert "Seção I" in art7.secao


def test_paragraphs_and_incisos_inherit_article_context(parsed) -> None:
    incisos_of_art7 = [s for s in parsed.hierarchy if s.artigo == "7" and s.inciso]
    assert {s.inciso for s in incisos_of_art7} == {"I", "II"}

    paragrafos_of_art7 = [s for s in parsed.hierarchy if s.artigo == "7" and s.paragrafo]
    nums = {s.paragrafo for s in paragrafos_of_art7}
    assert {"1", "2"} <= nums


def test_paragrafo_unico_is_captured(parsed) -> None:
    assert any(s.paragrafo == "único" for s in parsed.hierarchy)


def test_amendment_article_with_letter_suffix(parsed) -> None:
    art_55a = next(
        (s for s in parsed.hierarchy if s.artigo == "55-A" and not s.paragrafo),
        None,
    )
    assert art_55a is not None
    assert "Autoridade Nacional de Proteção de Dados" in art_55a.text


def test_vetoed_articles_are_kept_with_vetado_marker(parsed) -> None:
    art_56 = next((s for s in parsed.hierarchy if s.artigo == "56"), None)
    assert art_56 is not None
    assert "(VETADO)" in art_56.text


def test_closing_signature_line_is_ignored(parsed) -> None:
    all_text = " ".join(s.text for s in parsed.hierarchy)
    assert "Brasília, 14 de agosto de 2018" not in all_text
