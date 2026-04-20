"""Planalto scraper + parser for the LGPD (Lei 13.709/2018) consolidated text.

Two independent entry points:
- `fetch_raw()`: idempotent HTTP fetch with disk cache. Returns raw bytes.
- `parse_lgpd(html_bytes)`: pure function, bytes → NormalizedDocument.

The split lets tests exercise parsing against a checked-in fixture without
hitting the network, and lets us evolve the parser offline by re-running it
against cached raw HTML in `data/raw/`.

Planalto quirks handled here (all observed on 2026-04-17 fetch):
- Latin-1 encoding (served with no charset header; UTF-8 decode fails).
- Requires browser-like User-Agent (generic clients get connection reset).
- Legacy Word-generated markup: article/paragraph/inciso/section markers all
  live inside `<p class="Artigo">` distinguished only by leading text pattern.
- Amendments kept inline for audit: revoked text marked either with `<s>` /
  `<strike>` tags or via inline `text-decoration: line-through` CSS. We skip
  any `<p>` matching either.
- Amendment articles numbered with letter suffix (55-A, 58-B, ...).
- Vetoed articles render as literal "Art. N. (VETADO).".
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag
from core.schema import NormalizedDocument, Section
from tenacity import retry, stop_after_attempt, wait_exponential

LGPD_URL = "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm"
LGPD_ENACTED = date(2018, 8, 14)

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
    "themis-ingest/0.1 (+https://github.com/GMORETT/themis)"
)

_ART_RE = re.compile(r"^Art\.\s*(\d+)[ºo°]?(?:-([A-Z]))?\b")
_PARAGRAFO_RE = re.compile(r"^§\s*(\d+)[ºo°]?")
_PARAGRAFO_UNICO_RE = re.compile(r"^Parágrafo único", re.IGNORECASE)
_INCISO_RE = re.compile(r"^([IVX]+)\s*[-\u2013\u2014]")
_CAPITULO_RE = re.compile(r"^CAP[IÍ]TULO\s+([IVXLC]+)", re.IGNORECASE)
_SECAO_RE = re.compile(r"^Se[cç][aã]o\s+([IVXLC]+)", re.IGNORECASE)
_CLOSING_RE = re.compile(r"^Bras[íi]lia,\s")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _http_get(url: str) -> bytes:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(
            url, headers={"User-Agent": _USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"}
        )
        response.raise_for_status()
        return response.content


def fetch_raw(cache_path: Path, url: str = LGPD_URL) -> bytes:
    """Fetch URL to cache_path if missing. Idempotent: re-runs skip the HTTP call."""
    if cache_path.exists():
        return cache_path.read_bytes()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = _http_get(url)
    cache_path.write_bytes(data)
    return data


def _is_revoked(p: Tag) -> bool:
    if p.find(["s", "strike"]):
        return True
    for el in p.find_all(style=True):
        style = el.get("style")
        if isinstance(style, str) and "line-through" in style.lower():
            return True
    return False


def _split_capitulo_secao(text: str) -> tuple[str, str]:
    """Planalto concatenates roman numeral and title without a space.

    Example input: "CAPÍTULO II DO TRATAMENTO DE DADOS PESSOAIS"
    Returns: ("II", "Do Tratamento de Dados Pessoais").
    """
    match = re.match(r"^(?:CAP[IÍ]TULO|Se[cç][aã]o)\s+([IVXLC]+)\s*(.*)$", text, re.IGNORECASE)
    if not match:
        return "", text
    return match.group(1), match.group(2).strip()


def parse_lgpd(html_bytes: bytes) -> NormalizedDocument:
    """Parse Planalto LGPD HTML into a NormalizedDocument with flat Section list.

    The hierarchy is encoded on each Section: every `artigo`-level section carries
    the active `capitulo` and `secao` context so downstream chunkers can attach
    metadata without a tree walk.

    Encoding: real Planalto HTML is Latin-1 (no charset header). Fixtures and other
    sources may be UTF-8. Try UTF-8 first, then Latin-1 — both are stable for this
    content since we never mix encodings within a single document.
    """
    try:
        html = html_bytes.decode("utf-8")
    except UnicodeDecodeError:
        html = html_bytes.decode("latin-1")
    soup = BeautifulSoup(html, "lxml")

    sections: list[Section] = []
    current_capitulo: str | None = None
    current_secao: str | None = None
    current_artigo: str | None = None

    for p in soup.find_all("p"):
        if _is_revoked(p):
            continue
        text = p.get_text(separator=" ", strip=True).replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text)
        if not text or _CLOSING_RE.match(text):
            continue

        if m := _CAPITULO_RE.match(text):
            num, title = _split_capitulo_secao(text)
            current_capitulo = f"CAPÍTULO {num} — {title}" if title else f"CAPÍTULO {num}"
            current_secao = None
            continue

        if m := _SECAO_RE.match(text):
            num, title = _split_capitulo_secao(text)
            current_secao = f"Seção {num} — {title}" if title else f"Seção {num}"
            continue

        if m := _ART_RE.match(text):
            num = m.group(1)
            suffix = m.group(2)
            current_artigo = f"{num}-{suffix}" if suffix else num
            sections.append(
                Section(
                    capitulo=current_capitulo,
                    secao=current_secao,
                    artigo=current_artigo,
                    text=text,
                )
            )
            continue

        if m := _PARAGRAFO_RE.match(text):
            sections.append(
                Section(
                    capitulo=current_capitulo,
                    secao=current_secao,
                    artigo=current_artigo,
                    paragrafo=m.group(1),
                    text=text,
                )
            )
            continue

        if _PARAGRAFO_UNICO_RE.match(text):
            sections.append(
                Section(
                    capitulo=current_capitulo,
                    secao=current_secao,
                    artigo=current_artigo,
                    paragrafo="único",
                    text=text,
                )
            )
            continue

        if m := _INCISO_RE.match(text):
            sections.append(
                Section(
                    capitulo=current_capitulo,
                    secao=current_secao,
                    artigo=current_artigo,
                    inciso=m.group(1),
                    text=text,
                )
            )
            continue

    return NormalizedDocument(
        id="lgpd-13709-2018",
        source="planalto",
        source_url=LGPD_URL,
        doc_type="lei",
        title="Lei Geral de Proteção de Dados Pessoais (LGPD) — Lei nº 13.709/2018",
        jurisdiction="BR",
        enacted_at=LGPD_ENACTED,
        fetched_at=datetime.now(UTC),
        hierarchy=sections,
    )
