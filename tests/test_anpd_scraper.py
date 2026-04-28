"""Tests for the ANPD scraper helpers.

Tests focus on offline behavior — URL parsing, text extraction logic, slug
disambiguation, and section splitting. Network calls are not exercised here;
they're covered by the validate_corpus.py smoke checks against a live index.
"""

from __future__ import annotations

import pytest
from ingestion.sources.anpd import (
    _KNOWN_GUIDES,
    _extract_anpd_page_text,
    _extract_dou_text,
    _parse_date,
    _slug,
    _text_to_sections,
    _title_from_text,
)


def test_slug_disambiguates_guides_sharing_a_path() -> None:
    base = "https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes"
    s1 = _slug(f"{base}/guia_da_atuacao_do_encarregado_anpd.pdf/@@download/file")
    s2 = _slug(f"{base}/guia_legitimo_interesse.pdf/@@download/file")
    assert s1 != s2
    assert "encarregado" in s1
    assert "legitimo" in s2 or "leg-timo" in s2


def test_slug_falls_back_for_non_pdf_urls() -> None:
    s = _slug("https://www.in.gov.br/web/dou/-/resolucao-cd-anpd-n-15-de-24-de-abril-de-2024")
    assert "resolucao" in s
    assert len(s) <= 80


def test_known_guides_are_well_formed() -> None:
    assert len(_KNOWN_GUIDES) >= 4
    for title, url in _KNOWN_GUIDES:
        assert title.startswith("Guia")
        assert url.startswith("https://www.gov.br/anpd/")
        assert url.endswith("/@@download/file")


@pytest.mark.parametrize(
    "url,expected",
    [
        (
            "https://www.in.gov.br/web/dou/-/resolucao-cd-anpd-n-15-de-24-de-abril-de-2024-12345",
            "2024-04-24",
        ),
        (
            "https://www.in.gov.br/web/dou/-/resolucao-cd-anpd-n-10-de-5-de-dezembro-de-2023-99999",
            "2023-12-05",
        ),
        ("https://www.gov.br/anpd/no-date-here", None),
    ],
)
def test_parse_date_from_dou_url(url: str, expected: str | None) -> None:
    assert _parse_date(url) == expected


def test_extract_dou_text_pulls_from_texto_dou_div() -> None:
    html = """
    <html><body>
      <header>nav garbage</header>
      <div class="texto-dou">
        RESOLUÇÃO Nº 1, DE 1º DE JANEIRO DE 2024.
        O CONSELHO DIRETOR resolve aprovar o regulamento.
      </div>
      <footer>more garbage</footer>
    </body></html>
    """
    text = _extract_dou_text(html)
    assert "RESOLUÇÃO" in text
    assert "garbage" not in text
    assert "  " not in text  # whitespace normalized


def test_extract_anpd_page_text_picks_largest_unnamed_div() -> None:
    body = "RESOLUÇÃO blah " * 200  # >1000 chars and contains the keyword
    html = f"""
    <html><body>
      <div class="navbar">menu</div>
      <div>{body}</div>
      <div>tiny RESOLUÇÃO snippet</div>
    </body></html>
    """
    text = _extract_anpd_page_text(html)
    assert "RESOLUÇÃO" in text
    assert len(text) > 1000


def test_text_to_sections_assigns_sequential_artigo() -> None:
    text = (
        "Primeiro parágrafo da resolução com texto suficiente.\n\n"
        "Segundo bloco também legítimo aqui.\n\nx"
    )
    sections = _text_to_sections(text)
    # The third "x" is < 20 chars so should be filtered out.
    assert len(sections) == 2
    assert [s.artigo for s in sections] == ["1", "2"]
    assert sections[0].text.startswith("Primeiro")


def test_text_to_sections_falls_back_when_empty() -> None:
    sections = _text_to_sections("a b c")  # too short for paragraph split
    assert len(sections) == 1
    assert sections[0].artigo == "1"


def test_title_from_text_is_truncated() -> None:
    long = "RESOLUÇÃO CD/ANPD Nº 99 " + ("blah " * 100)
    title = _title_from_text(long)
    assert title.startswith("RESOLUÇÃO")
    assert len(title) <= 120
