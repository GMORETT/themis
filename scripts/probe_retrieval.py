"""One-shot debug script for hybrid retrieval against the live Qdrant index."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "packages"))
sys.path.insert(0, str(REPO / "apps"))

from rag.retrieval import HybridRetriever  # noqa: E402

r = HybridRetriever.from_chunks_jsonl(REPO / "data" / "processed" / "v1" / "chunks.jsonl")

for q in [
    "encarregado de proteção de dados",
    "encarregado",
    "Art. 41",
]:
    print(f"\n=== query: {q!r}")
    results = r.retrieve(q, top_k=10)
    print(f"  {len(results)} results")
    for i, x in enumerate(results):
        src = x.get("source")
        dt = x.get("doc_type")
        art = x.get("article_num")
        score = x.get("score")
        text = str(x.get("text", ""))[:80].replace("\n", " ")
        print(f"  [{i}] src={src} type={dt} art={art} score={score:.3f}  {text!r}")
