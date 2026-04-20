"""Domain schema for Themis ingestion pipeline.

Two layers:
- RawDocument: pointer to raw scraped artifact on disk
- NormalizedDocument: parsed, hierarchy-preserved canonical form (serialized to JSONL)
- Section: one node in the legal-text hierarchy (capítulo → seção → artigo → §/inciso)
- Chunk: retrieval unit produced by the chunker (Phase 1B), indexed in Qdrant (Phase 1C)

These models are consumed by the chunker (Phase 1B) and the indexer (Phase 1C).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocType = Literal[
    "lei",
    "anpd_resolucao",
    "anpd_guia",
    "anpd_decisao",
]

Jurisdiction = Literal["BR", "EU"]


class Section(BaseModel):
    """One node in the structural hierarchy of a legal document.

    Not every legal text has every level — a simple article has just `artigo` and
    `text`; a complex one nests paragrafo / inciso. `text` is the leaf content at
    this node (parent levels carry title metadata only).
    """

    model_config = ConfigDict(extra="forbid")

    capitulo: str | None = None
    secao: str | None = None
    artigo: str | None = None
    paragrafo: str | None = None
    inciso: str | None = None
    text: str


class RawDocument(BaseModel):
    """Pointer to a raw artifact cached on disk. Used for reproducibility / audit."""

    model_config = ConfigDict(extra="forbid")

    source_url: str
    doc_type: DocType
    fetched_at: datetime
    raw_path: str


class NormalizedDocument(BaseModel):
    """Canonical form of a parsed legal document, preserving structural hierarchy."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="stable slug, e.g. 'lgpd-13709-2018'")
    source: str = Field(description="origin label, e.g. 'planalto', 'anpd'")
    source_url: str
    doc_type: DocType
    title: str
    jurisdiction: Jurisdiction = "BR"
    enacted_at: date | None = None
    fetched_at: datetime
    hierarchy: list[Section]


class Chunk(BaseModel):
    """Retrieval unit: a self-contained text snippet with full provenance metadata.

    Produced by the chunker from a NormalizedDocument; indexed in Qdrant with this
    payload so retrieval results carry enough context for the generator (Phase 2).
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="SHA-256 hex digest of (doc_id + text)")
    doc_id: str = Field(description="parent NormalizedDocument.id")
    source: str
    doc_type: DocType
    jurisdiction: Jurisdiction
    title: str = Field(description="parent document title")
    capitulo: str | None = None
    secao: str | None = None
    article_num: str | None = None
    paragraph_num: str | None = None
    inciso: str | None = None
    enacted_at: date | None = None
    text: str
    tokens_approx: int = Field(description="approximate token count via tiktoken cl100k")
