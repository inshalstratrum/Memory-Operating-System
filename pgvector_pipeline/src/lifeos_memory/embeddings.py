from __future__ import annotations

from functools import lru_cache

import numpy as np

from .contracts import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _model().encode(texts, normalize_embeddings=True)
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim != 2 or arr.shape[1] != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSIONS}, got {arr.shape}"
        )
    return arr.tolist()


def vector_literal(vector: list[float]) -> str:
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise ValueError(f"Expected {EMBEDDING_DIMENSIONS} values, got {len(vector)}")
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"
