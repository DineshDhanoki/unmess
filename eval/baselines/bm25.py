"""Small in-memory BM25 ranker used only by the benchmark harness."""

import math
import re
from collections import Counter

from unmess.models import Chunk


def tokens(value: str) -> list[str]:
    return re.findall(r"[^\W_]+", value.casefold(), re.UNICODE)


def rank_bm25(query: str, chunks: list[Chunk]) -> list[Chunk]:
    if not chunks:
        return []
    vectors = [Counter(tokens(chunk.text)) for chunk in chunks]
    avg_len = sum(sum(vector.values()) for vector in vectors) / len(vectors)
    terms = set(tokens(query))
    scored: list[tuple[float, Chunk]] = []
    for chunk, vector in zip(chunks, vectors, strict=True):
        score = 0.0
        for term in terms:
            df = sum(term in other for other in vectors)
            idf = math.log(1 + (len(vectors) - df + 0.5) / (df + 0.5))
            count = vector[term]
            norm = 1.2 * (0.25 + 0.75 * sum(vector.values()) / max(avg_len, 1))
            score += idf * count * 2.2 / (count + norm) if count else 0
        scored.append((score, chunk))
    return [chunk for _score, chunk in sorted(scored, key=lambda item: (-item[0], item[1].id))]
