"""Hybrid retrieval over the indexed Themis corpus.

Server-side fusion: Qdrant runs both the dense (text-embedding-3-large) and
sparse (BM25) prefetches and fuses with Reciprocal Rank Fusion in a single
round trip. This is the query-side counterpart to the hybrid index built in
Phase 1C/1D.

The BM25 encoder is built from chunks.jsonl at construction time — its vocab
must match what was used at index time, otherwise sparse-vector indices won't
align. `HybridRetriever.from_chunks_jsonl()` is the supported constructor.
"""

from __future__ import annotations

import json
from pathlib import Path

from qdrant_client import QdrantClient, models

from rag.embedder import Embedder, OpenAIEmbedder
from rag.index import COLLECTION, _get_client
from rag.sparse import BM25Encoder

DEFAULT_TOP_K = 5
DEFAULT_PREFETCH_K = 20


class HybridRetriever:
    """Dense + sparse retrieval with server-side RRF.

    Construct via `from_chunks_jsonl(...)` so the BM25 encoder is built from
    the same chunks the index was built from.
    """

    def __init__(
        self,
        encoder: BM25Encoder,
        embedder: Embedder | None = None,
        client: QdrantClient | None = None,
    ) -> None:
        self._bm25 = encoder
        self._embedder = embedder or OpenAIEmbedder()
        self._client = client or _get_client()

    @classmethod
    def from_chunks_jsonl(
        cls,
        chunks_path: Path,
        *,
        embedder: Embedder | None = None,
        client: QdrantClient | None = None,
    ) -> HybridRetriever:
        texts = [
            json.loads(line)["text"]
            for line in chunks_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return cls(BM25Encoder(texts), embedder=embedder, client=client)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        prefetch_k: int = DEFAULT_PREFETCH_K,
        source: str | None = None,
    ) -> list[dict[str, object]]:
        """Return top-k payloads ranked by RRF over dense + sparse prefetches.

        Falls back to dense-only search when the query has no overlap with the
        BM25 vocabulary (e.g. one-word foreign queries) — Qdrant rejects empty
        sparse vectors, so trying to fuse there would error.

        `source` restricts results to a single corpus slice (e.g. "planalto"
        for LGPD only or "anpd" for ANPD only). The Phase-4 router will use
        this to narrow retrieval per agent; for now it keeps the smoke tests
        deterministic when one slice dominates the corpus by volume.
        """
        dense_vec = self._embedder.embed([query])[0]
        sparse_terms = self._bm25.encode(query)
        qfilter = self._build_filter(source)

        if not sparse_terms:
            return self._dense_only(dense_vec, top_k=top_k, qfilter=qfilter)

        sparse_vec = models.SparseVector(
            indices=list(sparse_terms.keys()),
            values=list(sparse_terms.values()),
        )

        results = self._client.query_points(
            collection_name=COLLECTION,
            prefetch=[
                models.Prefetch(query=dense_vec, using="dense", limit=prefetch_k, filter=qfilter),
                models.Prefetch(query=sparse_vec, using="sparse", limit=prefetch_k, filter=qfilter),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        ).points
        return [{"score": r.score, **(r.payload or {})} for r in results]

    @staticmethod
    def _build_filter(source: str | None) -> models.Filter | None:
        if source is None:
            return None
        return models.Filter(
            must=[models.FieldCondition(key="source", match=models.MatchValue(value=source))]
        )

    def _dense_only(
        self,
        dense_vec: list[float],
        *,
        top_k: int,
        qfilter: models.Filter | None = None,
    ) -> list[dict[str, object]]:
        results = self._client.query_points(
            collection_name=COLLECTION,
            query=dense_vec,
            using="dense",
            limit=top_k,
            with_payload=True,
            query_filter=qfilter,
        ).points
        return [{"score": r.score, **(r.payload or {})} for r in results]
