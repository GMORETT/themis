"""Probe ANPD guide PDF URLs to find working download patterns.

Tries:
1. Direct .pdf GET
2. Plone @@download/file suffix
3. /view suffix (HTML page → look for download link)

Run: uv run python scripts/probe_anpd_guides.py
"""

from __future__ import annotations

import httpx

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
HEADERS = {"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"}

CANDIDATES = [
    "https://www.gov.br/anpd/pt-br/centrais-de-conteudo/centrais-de-conteudos-novo/materiais-educativos-e-publicacoes/guia_da_atuacao_do_encarregado_anpd.pdf",
    "https://www.gov.br/anpd/pt-br/documentos-e-publicacoes/guia-agentes-de-tratamento-e-encarregado-versao-1-0-defeso-eleitoral.pdf",
    "https://www.gov.br/anpd/pt-br/documentos-e-publicacoes/guia_lgpd_final.pdf",
    "https://www.gov.br/anpd/pt-br/documentos-e-publicacoes/guia-agentes-de-tratamento.pdf",
    "https://www.gov.br/anpd/pt-br/documentos-e-publicacoes/guia-poder-publico-anpd.pdf",
    "https://www.gov.br/anpd/pt-br/documentos-e-publicacoes/guia-transferencia-internacional-de-dados.pdf",
]

SUFFIXES = ["", "/@@download/file", "/view"]


def probe(url: str) -> tuple[int, str, int]:
    """Return (status, content-type, content-length)."""
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=20)
        ct = r.headers.get("content-type", "?")
        return r.status_code, ct, len(r.content)
    except Exception as e:
        return -1, f"err: {e}", 0


def main() -> None:
    for base in CANDIDATES:
        print(f"\n=== {base}")
        for suf in SUFFIXES:
            url = base + suf
            status, ct, size = probe(url)
            ok = "OK " if status == 200 and "pdf" in ct.lower() else "   "
            print(f"  {ok} [{status}] {ct[:40]:<40} {size:>10} bytes  +{suf or '(none)'}")


if __name__ == "__main__":
    main()
