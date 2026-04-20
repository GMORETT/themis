"""Qdrant indexer: creates hybrid collection and upserts Chunks.

Collection schema:
- Dense vector: 3072-d cosine (text-embedding-3-large)
- Sparse vector: BM25 (for hybrid retrieval in Phase 2)
- Payload: all Chunk fields for post-retrieval filtering and citation

Collection name is versioned (themis_lgpd_v1) so schema changes create a new
collection rather than mutating the existing one.
"""

from __future__ import annotations

import os

from core.schema import Chunk
from dotenv import load_dotenv
from qdrant_client import QdrantClient, models

from rag.sparse import BM25Encoder

load_dotenv()

COLLECTION = "themis_lgpd_v1"
DENSE_DIM = 3072
UPSERT_BATCH = 64


def _get_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY") or None
    return QdrantClient(url=url, api_key=api_key)


def ensure_collection(client: QdrantClient, *, rebuild: bool = False) -> None:
    exists = client.collection_exists(COLLECTION)
    if exists and rebuild:
        client.delete_collection(COLLECTION)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": models.VectorParams(size=DENSE_DIM, distance=models.Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(index=models.SparseIndexParams(on_disk=False))
            },
        )


def upsert_chunks(
    client: QdrantClient,
    chunks: list[Chunk],
    dense_vectors: list[list[float]],
    encoder: BM25Encoder,
) -> int:
    points: list[models.PointStruct] = []
    for chunk, dense in zip(chunks, dense_vectors, strict=True):
        sparse = encoder.encode_document(chunk.text)
        payload = chunk.model_dump()
        points.append(
            models.PointStruct(
                id=int(chunk.id, 16),
                vector={
                    "dense": dense,
                    "sparse": models.SparseVector(
                        indices=list(sparse.keys()),
                        values=list(sparse.values()),
                    ),
                },
                payload=payload,
            )
        )

    for i in range(0, len(points), UPSERT_BATCH):
        client.upsert(collection_name=COLLECTION, points=points[i : i + UPSERT_BATCH])

    return len(points)


def search(
    client: QdrantClient,
    query_vector: list[float],
    *,
    top_k: int = 5,
) -> list[dict[str, object]]:
    results = client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        using="dense",
        limit=top_k,
        with_payload=True,
    ).points
    return [{"score": r.score, **(r.payload or {})} for r in results]
