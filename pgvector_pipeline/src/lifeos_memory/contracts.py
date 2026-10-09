from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

PILLAR_ALIASES = {
    "DEEN": "deen",
    "TRANSCENDENT": "deen",
    "SPIRITUAL": "deen",
    "NAFS": "nafs_aql",
    "AQL": "nafs_aql",
    "NAFS_AQL": "nafs_aql",
    "VESSEL": "nafs_aql",
    "MAAL": "maal",
    "STEWARDSHIP": "maal",
    "NASL": "nasl_khalq",
    "KHALQ": "nasl_khalq",
    "NASL_KHALQ": "nasl_khalq",
    "WEB": "nasl_khalq",
}

PILLARS = {"deen", "nafs_aql", "maal", "nasl_khalq"}
MEMORY_TYPES = {
    "short_term",
    "long_term",
    "task",
    "persona",
    "semantic",
    "episodic",
    "agent",
    "archive",
}
TEMPORAL_STATES = {"active_memory", "historical", "deprecated"}
SENSITIVITY_LEVELS = {"public", "internal", "sensitive", "secret"}
CONSENT_LEVELS = {
    "suggestion",
    "draft",
    "low_risk_autopilot",
    "explicit_approval",
}


def normalize_pillar(value: str | None, fallback: str = "maal") -> str:
    if not value:
        return fallback
    normalized = value.strip().replace("-", "_").replace("/", "_").upper()
    if normalized in PILLAR_ALIASES:
        return PILLAR_ALIASES[normalized]
    lower = normalized.lower()
    if lower in PILLARS:
        return lower
    raise ValueError(f"Unknown LifeOS pillar: {value!r}")


@dataclass(slots=True)
class SourceDocument:
    path: Path
    text: str
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MemoryChunk:
    source_path: Path
    source_title: str
    content: str
    chunk_index: int
    pillar: str
    memory_kind: str = "semantic"
    collection_name: str = "lifeos_core"
    temporal_state: str = "active_memory"
    confidence_score: float = 0.5
    sensitivity: str = "internal"
    consent_level: str = "suggestion"
    sanitization_applied: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.pillar not in PILLARS:
            raise ValueError(f"Invalid pillar: {self.pillar}")
        if self.memory_kind not in MEMORY_TYPES:
            raise ValueError(f"Invalid memory kind: {self.memory_kind}")
        if self.temporal_state not in TEMPORAL_STATES:
            raise ValueError(f"Invalid temporal state: {self.temporal_state}")
        if self.sensitivity not in SENSITIVITY_LEVELS:
            raise ValueError(f"Invalid sensitivity: {self.sensitivity}")
        if self.consent_level not in CONSENT_LEVELS:
            raise ValueError(f"Invalid consent level: {self.consent_level}")
        if not 0 <= self.confidence_score <= 1:
            raise ValueError("confidence_score must be between 0 and 1")
