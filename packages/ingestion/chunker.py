"""Chunker: NormalizedDocument → list[Chunk].

Strategy (documented in docs/decisions/0003-chunking-strategy.md):

Level 1 — article-as-chunk:
  Group all Sections that share the same artigo (the article text plus its
  paragraphs and incisos) into a single Chunk. This preserves legal cohesion
  because readers of a law never interpret an inciso in isolation from its
  parent article.

Level 2 — split oversized articles:
  If the combined text exceeds MAX_TOKENS, split at natural boundaries in order
  of preference: § (parágrafo) → inciso → sentence. Each split preserves
  OVERLAP_TOKENS of the previous window to keep context intact at boundaries.

Token counting uses tiktoken cl100k_base (the same tokenizer family as
text-embedding-3-large) so the split threshold aligns with the embedding input.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from itertools import groupby

import tiktoken
from core.schema import Chunk, DocType, Jurisdiction, NormalizedDocument, Section

MAX_TOKENS = 500
OVERLAP_TOKENS = 50

_enc = tiktoken.get_encoding("cl100k_base")


def _count(text: str) -> int:
    return len(_enc.encode(text))


def _make_id(doc_id: str, text: str) -> str:
    digest = hashlib.sha256(f"{doc_id}\x00{text}".encode()).hexdigest()
    return digest[:16]


def _split_sentences(text: str) -> list[str]:
    """Naive Portuguese sentence splitter: split on '. ' or ';\n'."""
    parts = re.split(r"(?<=[.;])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def _pack_with_overlap(windows: list[str], max_tok: int, overlap_tok: int) -> list[str]:
    """Greedy bin-pack windows into chunks; prepend overlap from previous chunk."""
    if not windows:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_tok = 0

    for window in windows:
        w_tok = _count(window)
        if current_tok + w_tok > max_tok and current:
            chunks.append(" ".join(current))
            # carry last OVERLAP_TOKENS worth of text into next chunk
            tail: list[str] = []
            tail_tok = 0
            for piece in reversed(current):
                t = _count(piece)
                if tail_tok + t > overlap_tok:
                    break
                tail.insert(0, piece)
                tail_tok += t
            current = tail
            current_tok = tail_tok
        current.append(window)
        current_tok += w_tok

    if current:
        chunks.append(" ".join(current))

    return chunks


def _sections_to_chunks(
    sections: list[Section],
    *,
    doc_id: str,
    source: str,
    doc_type: DocType,
    jurisdiction: Jurisdiction,
    title: str,
    article_num: str,
    enacted_at: date | None,
) -> list[Chunk]:
    """Convert all Sections of one article into one or more Chunks."""
    combined = " ".join(s.text for s in sections)
    capitulo = sections[0].capitulo
    secao = sections[0].secao

    if _count(combined) <= MAX_TOKENS:
        return [
            Chunk(
                id=_make_id(doc_id, combined),
                doc_id=doc_id,
                source=source,
                doc_type=doc_type,
                jurisdiction=jurisdiction,
                title=title,
                capitulo=capitulo,
                secao=secao,
                article_num=article_num,
                paragraph_num=None,
                inciso=None,
                enacted_at=enacted_at,
                text=combined,
                tokens_approx=_count(combined),
            )
        ]

    # --- Level 2: oversized article — split at natural legal boundaries ---
    # Prefer splitting by parágrafo, then inciso, then sentence.
    windows: list[str] = []
    for sec in sections:
        if sec.paragrafo or sec.inciso:
            windows.append(sec.text)
        else:
            # article root: split into sentences as smallest granularity
            windows.extend(_split_sentences(sec.text) or [sec.text])

    raw_chunks = _pack_with_overlap(windows, MAX_TOKENS, OVERLAP_TOKENS)

    result: list[Chunk] = []
    for i, chunk_text in enumerate(raw_chunks):
        # attribute paragraph / inciso only when the chunk comes from a single section
        matching = [s for s in sections if s.text in chunk_text]
        para = matching[0].paragrafo if len(matching) == 1 else None
        inc = matching[0].inciso if len(matching) == 1 else None
        result.append(
            Chunk(
                id=_make_id(doc_id, f"{i}\x00{chunk_text}"),
                doc_id=doc_id,
                source=source,
                doc_type=doc_type,
                jurisdiction=jurisdiction,
                title=title,
                capitulo=capitulo,
                secao=secao,
                article_num=article_num,
                paragraph_num=para,
                inciso=inc,
                enacted_at=enacted_at,
                text=chunk_text,
                tokens_approx=_count(chunk_text),
            )
        )
    return result


def chunk_document(doc: NormalizedDocument) -> list[Chunk]:
    """Produce retrieval chunks from a NormalizedDocument."""
    chunks: list[Chunk] = []

    # group sections by artigo (preserving order)
    for artigo, group in groupby(doc.hierarchy, key=lambda s: s.artigo):
        sections = list(group)
        if artigo is None:
            # preamble / closing lines without an article — skip
            continue
        chunks.extend(
            _sections_to_chunks(
                sections,
                doc_id=doc.id,
                source=doc.source,
                doc_type=doc.doc_type,
                jurisdiction=doc.jurisdiction,
                title=doc.title,
                article_num=artigo,
                enacted_at=doc.enacted_at,
            )
        )

    return chunks
