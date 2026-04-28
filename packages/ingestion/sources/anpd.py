"""ANPD scraper: fetches CD/ANPD resolutions and guides.

Two entry points:
- `fetch_resolucoes(cache_dir)` → list[NormalizedDocument]
- `fetch_guias(cache_dir)` → list[NormalizedDocument]

Source strategy (discovered empirically on 2026-04-20):
- Resolutions index page at gov.br/anpd lists:
    a) DOU links (in.gov.br/en/web/dou/...) → text extracted from div.texto-dou
    b) ANPD-hosted detail pages → text in largest unnamed content div
- Guides: curated list of known official guide PDFs from the ANPD publications
  page (Plone renders links via JS so the list is maintained here).
- Rate-limit: 1 request / 2 s, Browser-like UA, robots.txt allows crawling.
"""

from __future__ import annotations

import re
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from core.schema import NormalizedDocument, Section
from tenacity import retry, stop_after_attempt, wait_exponential

from ingestion.sources.pdf_loader import extract_text

RESOLUCOES_INDEX = "https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd"
ANPD_BASE = "https://www.gov.br"
DOU_BASE = "https://www.in.gov.br"

_RATE_LIMIT_S = 2.0

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 "
    "themis-ingest/0.1 (+https://github.com/GMORETT/themis)"
)
_HEADERS = {"User-Agent": _UA, "Accept-Language": "pt-BR,pt;q=0.9"}

# Plone serves the binary at the @@download/file traversal — the bare .pdf
# path returns an HTML wrapper. URLs verified 2026-04-27 against the
# materials-educativos-e-publicacoes listing.
_GUIDES_BASE = (
    "https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes"
)
_KNOWN_GUIDES: list[tuple[str, str]] = [
    (
        "Guia Orientativo: Atuação do Encarregado pelo Tratamento de Dados Pessoais",
        f"{_GUIDES_BASE}/guia_da_atuacao_do_encarregado_anpd.pdf/@@download/file",
    ),
    (
        "Guia Orientativo: Definições dos Agentes de Tratamento e do Encarregado"
        " (contexto eleitoral)",
        f"{_GUIDES_BASE}/guia-agentes-de-tratamento-e-encarregado"
        "-versao-1-0-defeso-eleitoral.pdf/@@download/file",
    ),
    (
        "Guia Orientativo: Aplicação da LGPD por Agentes de Tratamento no contexto eleitoral",
        f"{_GUIDES_BASE}/guia_lgpd_final.pdf/@@download/file",
    ),
    (
        "Guia Orientativo: Hipóteses Legais de Tratamento — Legítimo Interesse",
        f"{_GUIDES_BASE}/guia_legitimo_interesse.pdf/@@download/file",
    ),
]


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _get(url: str) -> httpx.Response:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.get(url, headers=_HEADERS)
        response.raise_for_status()
        return response


def _get_with_rate_limit(url: str, last_request: list[float]) -> httpx.Response:
    elapsed = time.monotonic() - last_request[0]
    if elapsed < _RATE_LIMIT_S:
        time.sleep(_RATE_LIMIT_S - elapsed)
    response = _get(url)
    last_request[0] = time.monotonic()
    return response


def _slug(url: str) -> str:
    """URL → safe filename.

    For PDF download URLs, key off the .pdf basename so multiple guides served
    from the same Plone path don't collide after truncation.
    """
    path = url.lower().split("//")[-1]
    pdf_match = re.search(r"([a-z0-9_\-]+)\.pdf", path)
    if pdf_match:
        return re.sub(r"[^a-z0-9]+", "-", pdf_match.group(1))[:80]
    return re.sub(r"[^a-z0-9]+", "-", path)[:80]


def _extract_dou_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    div = soup.find("div", class_="texto-dou")
    if div:
        return re.sub(r"\s+", " ", div.get_text(separator=" ", strip=True))
    return ""


def _extract_anpd_page_text(html: str) -> str:
    """Extract text from ANPD-hosted resolution detail page.

    These pages render the full legal text in a nameless div. We find it by
    looking for the largest content block containing the resolution header.
    """
    soup = BeautifulSoup(html, "lxml")
    candidates = [
        d
        for d in soup.find_all("div")
        if not d.get("class") and "RESOLUÇÃO" in d.get_text() and len(d.get_text()) > 1000
    ]
    if not candidates:
        return ""
    best = max(candidates, key=lambda d: len(d.get_text()))
    return re.sub(r"\s+", " ", best.get_text(separator=" ", strip=True))


def _title_from_text(text: str) -> str:
    """Extract resolution title from text (first ~150 chars normalized)."""
    first = text[:200].strip()
    return first[:120]


def _parse_date(url: str) -> str | None:
    """Try to extract date from DOU URL slug."""
    m = re.search(r"-(\d{1,2})-de-([a-z]+)-de-(\d{4})", url)
    if not m:
        return None
    months = {
        "janeiro": "01",
        "fevereiro": "02",
        "março": "03",
        "marco": "03",
        "abril": "04",
        "maio": "05",
        "junho": "06",
        "julho": "07",
        "agosto": "08",
        "setembro": "09",
        "outubro": "10",
        "novembro": "11",
        "dezembro": "12",
    }
    day, month_name, year = m.group(1), m.group(2), m.group(3)
    month = months.get(month_name)
    if month:
        return f"{year}-{month}-{int(day):02d}"
    return None


def _text_to_sections(text: str) -> list[Section]:
    """Split resolution/guide text into paragraph-level Sections.

    Each paragraph gets a sequential artigo number so the chunker can group
    and split them — ANPD documents don't use LGPD-style article markers.
    """
    raw_parts = re.split(r"\n{2,}", text)
    sections: list[Section] = []
    for i, part in enumerate(raw_parts, start=1):
        part = part.strip()
        if len(part) < 20:
            continue
        sections.append(Section(artigo=str(i), text=part))
    if not sections:
        sections = [Section(artigo="1", text=text[:5000])]
    return sections


def _enumerate_resolucao_urls() -> list[tuple[str, str]]:
    """Fetch the ANPD resolutions index page and return (title, url) pairs."""
    response = _get(RESOLUCOES_INDEX)
    soup = BeautifulSoup(response.text, "lxml")

    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    for a in soup.find_all("a", href=True):
        href = str(a["href"])
        text = a.get_text(strip=True)

        # DOU resolution links
        is_dou = "in.gov.br/web/dou" in href or "in.gov.br/en/web/dou" in href
        if is_dou and "resolucao" in href.lower():
            if href not in seen:
                seen.add(href)
                results.append((text or href, href))
            continue

        # ANPD-hosted resolution pages
        if (
            "gov.br/anpd" in href
            and "resolucao" in href.lower()
            and "regulamentacoes_anpd" in href
            and ".pdf" not in href.lower()
            and href not in seen
        ):
            seen.add(href)
            results.append((text or href, href))

    return results


def fetch_resolucoes(cache_dir: Path) -> list[NormalizedDocument]:
    """Fetch all CD/ANPD resolutions. Returns list of NormalizedDocuments."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    entries = _enumerate_resolucao_urls()
    docs: list[NormalizedDocument] = []
    last_request: list[float] = [0.0]

    for i, (title_hint, url) in enumerate(entries):
        cache_file = cache_dir / f"{_slug(url)}.html"

        if cache_file.exists():
            raw = cache_file.read_text(encoding="utf-8")
        else:
            resp = _get_with_rate_limit(url, last_request)
            raw = resp.text
            cache_file.write_text(raw, encoding="utf-8")

        # Extract text
        text = _extract_dou_text(raw) if "in.gov.br" in url else _extract_anpd_page_text(raw)

        if not text or len(text) < 50:
            continue

        doc_title = _title_from_text(text) or title_hint
        date_str = _parse_date(url)

        import contextlib
        from datetime import date

        enacted = None
        if date_str:
            with contextlib.suppress(ValueError):
                enacted = date.fromisoformat(date_str)

        # derive stable slug from URL
        num_match = re.search(r"n[º°-]?\s*(\d+)", url, re.IGNORECASE)
        num = num_match.group(1) if num_match else str(i + 1)
        doc_id = f"anpd-resolucao-{num}"

        docs.append(
            NormalizedDocument(
                id=doc_id,
                source="anpd",
                source_url=url,
                doc_type="anpd_resolucao",
                title=doc_title,
                jurisdiction="BR",
                enacted_at=enacted,
                fetched_at=datetime.now(UTC),
                hierarchy=_text_to_sections(text),
            )
        )

    return docs


def fetch_guias(cache_dir: Path) -> list[NormalizedDocument]:
    """Fetch known ANPD guide PDFs. Returns list of NormalizedDocuments."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    docs: list[NormalizedDocument] = []
    last_request: list[float] = [0.0]

    for title, url in _KNOWN_GUIDES:
        cache_file = cache_dir / f"{_slug(url)}.pdf"

        if cache_file.exists():
            pdf_bytes = cache_file.read_bytes()
        else:
            try:
                resp = _get_with_rate_limit(url, last_request)
                pdf_bytes = resp.content
                cache_file.write_bytes(pdf_bytes)
            except Exception:
                continue

        try:
            text = extract_text(pdf_bytes)
        except Exception:
            continue

        if not text or len(text) < 100:
            continue

        slug = re.sub(r"[^a-z0-9]+", "-", title.lower())[:60]
        docs.append(
            NormalizedDocument(
                id=f"anpd-guia-{slug}",
                source="anpd",
                source_url=url,
                doc_type="anpd_guia",
                title=title,
                jurisdiction="BR",
                enacted_at=None,
                fetched_at=datetime.now(UTC),
                hierarchy=_text_to_sections(text),
            )
        )

    return docs
