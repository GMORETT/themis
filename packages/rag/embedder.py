"""Embedder ABC + OpenAI implementation.

Cost guard: before sending any batch, the estimated cost is checked against
COST_HARD_STOP_USD. If exceeded, RuntimeError is raised — no tokens consumed.

Pricing (as of 2026-04): text-embedding-3-large = $0.13 / 1M tokens.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

# $0.13 per 1M tokens (text-embedding-3-large, 2026-04)
_PRICE_PER_TOKEN = 0.13 / 1_000_000
COST_HARD_STOP_USD = 1.0
BATCH_SIZE = 100
MODEL = "text-embedding-3-large"
DIMENSIONS = 3072


class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text."""


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str = MODEL, dimensions: int = DIMENSIONS) -> None:
        self.model = model
        self.dimensions = dimensions
        self._client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    def _estimate_tokens(self, texts: list[str]) -> int:
        # rough upper bound: 1 token ≈ 4 chars (safe overestimate for Portuguese)
        return sum(len(t) // 4 + 1 for t in texts)

    def _check_cost(self, texts: list[str]) -> None:
        estimated = self._estimate_tokens(texts) * _PRICE_PER_TOKEN
        if estimated > COST_HARD_STOP_USD:
            raise RuntimeError(
                f"Estimated embedding cost ${estimated:.4f} exceeds hard stop "
                f"${COST_HARD_STOP_USD:.2f}. Aborting — no tokens consumed."
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_api(self, batch: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            input=batch,
            model=self.model,
            dimensions=self.dimensions,
        )
        return [item.embedding for item in response.data]

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._check_cost(texts)
        results: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            results.extend(self._call_api(batch))
        return results

    def embed_with_usage(self, texts: list[str]) -> tuple[list[list[float]], int]:
        """Embed and return (vectors, total_tokens). Used by CLI for cost logging."""
        self._check_cost(texts)
        results: list[list[float]] = []
        total_tokens = 0
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            response = self._client.embeddings.create(
                input=batch,
                model=self.model,
                dimensions=self.dimensions,
            )
            results.extend(item.embedding for item in response.data)
            total_tokens += response.usage.total_tokens
        return results, total_tokens
