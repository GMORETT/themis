"""BM25 sparse encoder for hybrid search in Qdrant.

Tokenizer: lowercase + split on non-alphanumeric (handles Portuguese without
requiring a full NLP library). Good enough for legal text retrieval where
exact term overlap matters more than morphological normalization.
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]


def _tokenize(text: str) -> list[str]:
    return re.sub(r"[^a-záéíóúãõâêîôûàèìòùçñ0-9]", " ", text.lower()).split()


class BM25Encoder:
    def __init__(self, corpus: list[str]) -> None:
        tokenized = [_tokenize(doc) for doc in corpus]
        self._bm25 = BM25Okapi(tokenized)
        # build vocab: token → index
        self._vocab: dict[str, int] = {}
        for tokens in tokenized:
            for t in tokens:
                if t not in self._vocab:
                    self._vocab[t] = len(self._vocab)

    def encode(self, text: str) -> dict[int, float]:
        """Return {token_index: bm25_score} sparse vector for a query."""
        tokens = _tokenize(text)
        scores = self._bm25.get_scores(tokens)
        return {
            self._vocab[t]: float(scores[self._vocab[t]])
            for t in tokens
            if t in self._vocab and scores[self._vocab[t]] > 0
        }

    def encode_document(self, text: str) -> dict[int, float]:
        """Return {token_index: tf} sparse vector for a document."""
        tokens = _tokenize(text)
        tf: dict[int, float] = {}
        for t in tokens:
            if t not in self._vocab:
                self._vocab[t] = len(self._vocab)
            idx = self._vocab[t]
            tf[idx] = tf.get(idx, 0.0) + 1.0
        return tf
