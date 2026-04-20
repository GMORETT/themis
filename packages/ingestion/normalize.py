"""JSONL serializer for NormalizedDocument.

One document per line. Datetimes serialized as ISO-8601 strings by Pydantic.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from core.schema import NormalizedDocument


def write_jsonl(docs: Iterable[NormalizedDocument], path: Path) -> int:
    """Write documents as JSONL. Returns the number of lines written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(doc.model_dump_json())
            f.write("\n")
            count += 1
    return count


def read_jsonl(path: Path) -> list[NormalizedDocument]:
    with path.open("r", encoding="utf-8") as f:
        return [NormalizedDocument.model_validate_json(line) for line in f if line.strip()]
