from __future__ import annotations

from collections import Counter

from .contracts import normalize_pillar

KEYWORDS = {
    "deen": {
        "allah", "akhirah", "deen", "faith", "fajr", "quran", "dhikr", "adhkar",
        "ibadah", "salah", "taqwa", "tawakkul", "zakat", "sadaqah", "haram", "halal",
        "muhasabah", "niyyah", "khushu",
    },
    "nafs_aql": {
        "nafs", "aql", "sleep", "fitness", "nutrition", "health", "mental",
        "cognitive", "learning", "intellect", "body", "energy", "readiness",
        "agentic", "python", "torch", "embedding", "minilm", "hardware", "rtx",
    },
    "maal": {
        "maal", "money", "finance", "ledger", "client", "upwork", "proposal",
        "freelance", "spicy", "crust", "business", "revenue", "supabase", "langflow",
        "postgres", "project", "task", "workflow", "docker", "agency", "career",
    },
    "nasl_khalq": {
        "nasl", "khalq", "family", "community", "relationship", "huquq", "ihsan",
        "network", "client psychology", "communication", "ummah", "social",
        "parents", "team",
    },
}


def classify_pillar(text: str, requested: str | None = None) -> str:
    if requested and requested.lower() != "auto":
        return normalize_pillar(requested)

    tokens = text.lower()
    scores: Counter[str] = Counter()
    for pillar, keywords in KEYWORDS.items():
        for keyword in keywords:
            if keyword in tokens:
                scores[pillar] += 1

    if not scores:
        return "maal"
    return scores.most_common(1)[0][0]
