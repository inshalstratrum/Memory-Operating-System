from __future__ import annotations

import re

WORD_RE = re.compile(r"\S+")


def chunk_words(text: str, chunk_words: int = 250, overlap_ratio: float = 0.15) -> list[str]:
    words = WORD_RE.findall(text)
    if not words:
        return []
    if chunk_words <= 0:
        raise ValueError("chunk_words must be positive")
    overlap = max(0, min(int(chunk_words * overlap_ratio), chunk_words - 1))
    step = chunk_words - overlap
    chunks: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_words]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_words >= len(words):
            break
    return chunks
