from __future__ import annotations

"""LifeOS Phase 1 temporal fusion retriever.

This Langflow component owns only the Advanced RAG retrieval step:
- generate a local all-MiniLM-L6-v2 384D query embedding;
- enforce LifeOS 4-Pillar isolation and controlled bridge rules;
- call a local server-side memory API that owns Supabase credentials;
- fuse candidates with weighted RRF, temporal decay, and MMR diversity.

It deliberately contains no database credential input. The current memory API can
use match_life_memories behind the scenes, and a later Phase 2/3 gateway can
swap that server endpoint to lifeos_hybrid_search without changing this node's
Langflow contract.
"""

import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

import httpx
from langflow.custom import Component
from langflow.io import (
    BoolInput,
    DataInput,
    DropdownInput,
    FloatInput,
    IntInput,
    MessageInput,
    MultilineInput,
    Output,
    StrInput,
)
from langflow.schema import Data

try:
    from lifeos_contracts import RouteManifest, model_payload
except ImportError:
    from .lifeos_contracts import RouteManifest, model_payload

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

VALID_PILLARS = {"deen", "nafs_aql", "maal", "nasl_khalq"}
PILLAR_ALIASES = {
    "DEEN": "deen",
    "NAFS": "nafs_aql",
    "AQL": "nafs_aql",
    "NAFS_AQL": "nafs_aql",
    "NAFS/AQL": "nafs_aql",
    "MAAL": "maal",
    "NASL": "nasl_khalq",
    "KHALQ": "nasl_khalq",
    "NASL_KHALQ": "nasl_khalq",
    "NASL/KHALQ": "nasl_khalq",
}

QUERY_PROFILES = {"conceptual", "identifier", "relational", "temporal"}
QUERY_GROUP_WEIGHTS = {
    "conceptual": {"dense": 1.0, "lexical": 0.7, "entity": 0.7},
    "identifier": {"dense": 0.75, "lexical": 1.15, "entity": 1.05},
    "relational": {"dense": 0.75, "lexical": 0.85, "entity": 1.2},
    "temporal": {"dense": 0.85, "lexical": 0.9, "entity": 0.75},
}

SENSITIVE_LEVELS = {"sensitive", "secret"}
NO_DECAY_KINDS = {"canonical", "persona"}
TEMPORAL_HALF_LIVES_DAYS = {
    "short_term": 2.0,
    "short-term": 2.0,
    "short": 2.0,
    "task": 7.0,
    "tasks": 7.0,
    "agent_trace": 30.0,
    "agent_traces": 30.0,
    "agent-trace": 30.0,
    "episodic": 45.0,
    "semantic": 365.0,
}

NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,254}$")
SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|authorization|bearer|credential|jwt|password|pin|secret|service[_-]?role|token)",
    re.IGNORECASE,
)

BRIDGE_CONFIDENCE_THRESHOLD = 0.75
MAX_RELATED_PILLARS = 2
PRIMARY_LANE_WEIGHT = 1.0
RELATED_LANE_WEIGHT = 0.75
CANDIDATES_PER_LANE = 40
RRF_K = 60
MMR_LAMBDA = 0.75
MMR_CANDIDATE_LIMIT = 20
MAX_RESULT_COUNT = 40

DEFAULT_MEMORY_API_URL = os.getenv(
    "LIFEOS_MEMORY_API_URL",
    "http://host.docker.internal:3000/api/memory",
)


@lru_cache(maxsize=1)
def _embedding_model() -> Any:
    """Lazy-load MiniLM so Langflow can import the component before deps load."""

    try:
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "sentence-transformers is required in the Langflow runtime for "
            "local all-MiniLM-L6-v2 384D embeddings."
        ) from exc
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def generate_local_embedding(text: str) -> list[float]:
    """Dense retrieval starts here: query/candidate text becomes a local 384D vector."""

    clean_text = str(text or "").strip()
    if not clean_text:
        raise ValueError("Cannot embed empty text")
    model = _embedding_model()
    try:
        encoded = model.encode([clean_text], normalize_embeddings=True)
    except TypeError:
        encoded = model.encode([clean_text])
    first = encoded[0] if isinstance(encoded, Sequence) else encoded
    return validate_embedding(first)


def validate_embedding(value: Any) -> list[float]:
    candidate = value.data if isinstance(value, Data) else value
    if isinstance(candidate, Mapping):
        for key in ("embedding", "embeddings", "vector", "query_embedding", "queryEmbedding"):
            if key in candidate:
                candidate = candidate[key]
                break
    if hasattr(candidate, "tolist"):
        candidate = candidate.tolist()
    if (
        isinstance(candidate, Sequence)
        and not isinstance(candidate, (str, bytes, bytearray))
        and len(candidate) == 1
        and isinstance(candidate[0], Sequence)
        and not isinstance(candidate[0], (str, bytes, bytearray))
    ):
        candidate = candidate[0]
    if isinstance(candidate, str):
        try:
            candidate = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ValueError("Embedding must be a JSON array or structured Data value") from exc
    if not isinstance(candidate, Sequence) or isinstance(candidate, (str, bytes, bytearray)):
        raise ValueError("Embedding must be a numeric sequence")
    if len(candidate) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Embedding must contain exactly {EMBEDDING_DIMENSIONS} values; got {len(candidate)}"
        )

    embedding: list[float] = []
    for index, item in enumerate(candidate):
        try:
            number = float(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Embedding value at index {index} is not numeric") from exc
        if not math.isfinite(number):
            raise ValueError(f"Embedding value at index {index} must be finite")
        embedding.append(number)
    return embedding


def normalize_pillar(value: str) -> str:
    key = value.strip().replace("-", "_").upper()
    pillar = PILLAR_ALIASES.get(key, key.lower())
    if pillar not in VALID_PILLARS:
        raise ValueError(f"Unknown LifeOS pillar: {value!r}")
    return pillar


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_bridge_reasons(value: str | Mapping[str, Any] | None) -> dict[str, str]:
    if value is None or value == "":
        return {}
    if isinstance(value, Mapping):
        raw = dict(value)
    else:
        try:
            raw = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError("Bridge reasons must be a JSON object keyed by pillar") from exc
    if not isinstance(raw, dict):
        raise ValueError("Bridge reasons must be a JSON object keyed by pillar")

    reasons: dict[str, str] = {}
    for key, reason in raw.items():
        pillar = normalize_pillar(str(key))
        text = str(reason).strip()
        if text:
            reasons[pillar] = text
    return reasons


def resolve_search_lanes(
    active_pillar: str,
    related_pillars: str | Sequence[str],
    bridge_reasons: str | Mapping[str, Any] | None,
    router_confidence: float,
    *,
    reject_invalid: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Pillar isolation is enforced before any retrieval request is allowed."""

    primary = normalize_pillar(active_pillar)
    related_values = (
        _split_csv(related_pillars)
        if isinstance(related_pillars, str)
        else [str(item).strip() for item in related_pillars if str(item).strip()]
    )
    if len(related_values) > MAX_RELATED_PILLARS:
        raise ValueError(f"At most {MAX_RELATED_PILLARS} related pillars may be requested")

    normalized_related: list[str] = []
    for value in related_values:
        pillar = normalize_pillar(value)
        if pillar not in normalized_related:
            normalized_related.append(pillar)
    if len(normalized_related) > MAX_RELATED_PILLARS:
        raise ValueError(f"At most {MAX_RELATED_PILLARS} unique related pillars may be requested")

    reasons = parse_bridge_reasons(bridge_reasons)
    accepted = [
        {
            "pillar": primary,
            "kind": "primary",
            "weight": PRIMARY_LANE_WEIGHT,
            "bridge_reason": None,
        }
    ]
    rejected: list[dict[str, str]] = []
    for pillar in normalized_related:
        reason = reasons.get(pillar, "")
        if pillar == primary:
            rejected.append({"pillar": pillar, "reason": "same_as_active_pillar"})
        elif router_confidence < BRIDGE_CONFIDENCE_THRESHOLD:
            rejected.append({"pillar": pillar, "reason": "router_confidence_below_0.75"})
        elif not reason:
            rejected.append({"pillar": pillar, "reason": "missing_bridge_reason"})
        else:
            accepted.append(
                {
                    "pillar": pillar,
                    "kind": "related",
                    "weight": RELATED_LANE_WEIGHT,
                    "bridge_reason": reason,
                }
            )

    if reject_invalid and rejected:
        details = ", ".join(f"{item['pillar']}:{item['reason']}" for item in rejected)
        raise ValueError(f"Related pillar bridge rejected before retrieval: {details}")
    return accepted, rejected


def validate_namespaces(namespace: str | Sequence[str], project_id: str | None) -> list[str]:
    values = (
        _split_csv(namespace)
        if isinstance(namespace, str)
        else [str(item).strip() for item in namespace if str(item).strip()]
    )
    if not values:
        values = ["lifeos_core"]

    unique: list[str] = []
    for value in values:
        if not NAMESPACE_PATTERN.fullmatch(value):
            raise ValueError(f"Invalid memory namespace: {value!r}")
        if value not in unique:
            unique.append(value)

    client_namespaces = [item for item in unique if item.startswith("client_")]
    normalized_project = (project_id or "").strip()
    if client_namespaces and not normalized_project:
        raise ValueError("An exact project ID is required for client namespaces")
    if client_namespaces:
        expected = (
            normalized_project
            if normalized_project.startswith("client_")
            else f"client_{normalized_project}"
        )
        if any(item != expected for item in client_namespaces):
            raise ValueError("Cross-client namespace access denied")

    if "lifeos_core" not in unique:
        unique.append("lifeos_core")
    return unique


def reciprocal_rank_fusion(
    lane_results: Sequence[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]],
    rrf_k: int = RRF_K,
) -> list[dict[str, Any]]:
    """RRF scoring happens here across dense/future-hybrid groups and pillar lanes."""

    if rrf_k <= 0:
        raise ValueError("RRF k must be positive")
    candidates: dict[str, dict[str, Any]] = {}

    for lane, rows in lane_results:
        lane_weight = float(lane["weight"])
        for rank, row in enumerate(rows, start=1):
            memory_id = str(row.get("id") or row.get("memory_id") or "").strip()
            if not memory_id:
                continue
            contribution = lane_weight / (rrf_k + rank)
            existing = candidates.get(memory_id)
            if existing is None:
                existing = {
                    **dict(row),
                    "id": memory_id,
                    "_rrf_raw": 0.0,
                    "_lane_hits": [],
                    "_bridge_reasons": [],
                    "_candidate_groups": [],
                }
                candidates[memory_id] = existing
            elif _score_value(row) > _score_value(existing):
                preserved = {
                    "_rrf_raw": existing["_rrf_raw"],
                    "_lane_hits": existing["_lane_hits"],
                    "_bridge_reasons": existing["_bridge_reasons"],
                    "_candidate_groups": existing["_candidate_groups"],
                }
                existing.update(dict(row))
                existing.update(preserved)

            existing["_rrf_raw"] += contribution
            existing["_lane_hits"].append(
                {
                    "pillar": lane["pillar"],
                    "kind": lane["kind"],
                    "rank": rank,
                    "weight": lane_weight,
                    "group": lane.get("group", "dense"),
                }
            )
            existing["_candidate_groups"].append(str(lane.get("group", "dense")))
            if lane.get("bridge_reason"):
                existing["_bridge_reasons"].append(
                    {"pillar": lane["pillar"], "reason": lane["bridge_reason"]}
                )

    fused = list(candidates.values())
    normalized_rrf = _min_max([item["_rrf_raw"] for item in fused])
    for item, score in zip(fused, normalized_rrf, strict=True):
        item["rrf_score"] = score
    return fused


def apply_temporal_decay(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Temporal decay happens here using the plan's half-life schedule."""

    now = datetime.now(timezone.utc)
    missing_timestamps = 0
    for item in candidates:
        decay, reason = temporal_decay_score(item, now)
        if reason == "missing_timestamp":
            missing_timestamps += 1
        item["temporal_decay_score"] = decay
        item["temporal_decay_reason"] = reason
    return candidates, missing_timestamps


def temporal_decay_score(row: Mapping[str, Any], now: datetime | None = None) -> tuple[float, str]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
    memory_kind = str(row.get("memory_kind") or metadata.get("memory_kind") or "").lower()
    temporal_state = str(row.get("temporal_state") or metadata.get("temporal_state") or "").lower()
    collection_name = str(row.get("collection_name") or row.get("namespace") or "").lower()

    if memory_kind in NO_DECAY_KINDS or metadata.get("canonical") is True:
        return 1.0, "no_decay"
    if collection_name in {"lifeos_core", "shali_core"} and metadata.get("canonical") is True:
        return 1.0, "no_decay"

    half_life = (
        TEMPORAL_HALF_LIVES_DAYS.get(memory_kind)
        or TEMPORAL_HALF_LIVES_DAYS.get(temporal_state)
        or TEMPORAL_HALF_LIVES_DAYS.get(str(metadata.get("decay_profile", "")).lower())
    )
    if half_life is None:
        half_life = TEMPORAL_HALF_LIVES_DAYS["semantic"]

    timestamp = _parse_timestamp(
        row.get("last_accessed_at")
        or row.get("created_at")
        or metadata.get("last_accessed_at")
        or metadata.get("created_at")
        or metadata.get("event_time")
        or metadata.get("timestamp")
    )
    if timestamp is None:
        return 1.0, "missing_timestamp"

    current = now or datetime.now(timezone.utc)
    age_days = max(0.0, (current - timestamp).total_seconds() / 86400.0)
    return 0.5 ** (age_days / half_life), f"half_life_{half_life:g}d"


def calculate_fusion_scores(candidates: list[dict[str, Any]], query_profile: str) -> list[dict[str, Any]]:
    dense_values = [_score_value(item) for item in candidates]
    normalized_dense = _min_max(dense_values)
    weights = _profile_score_weights(query_profile)

    for item, dense_score in zip(candidates, normalized_dense, strict=True):
        source_authority = _source_authority_score(item)
        confidence = _clamp01(_as_float(item.get("confidence_score"), 0.5))
        temporal = _clamp01(_as_float(item.get("temporal_decay_score"), 1.0))
        rrf = _clamp01(_as_float(item.get("rrf_score"), 0.0))
        item["dense_score"] = dense_score
        item["source_authority_score"] = source_authority
        item["confidence_component"] = confidence
        item["fusion_score"] = (
            weights["dense"] * dense_score
            + weights["rrf"] * rrf
            + weights["source"] * source_authority
            + weights["confidence"] * confidence
            + weights["temporal"] * temporal
        )

    return sorted(
        candidates,
        key=lambda item: (
            -_as_float(item.get("fusion_score")),
            -_as_float(item.get("rrf_score")),
            str(item.get("id", "")),
        ),
    )


def apply_mmr(
    candidates: Sequence[Mapping[str, Any]],
    embeddings: Mapping[str, Sequence[float]],
    result_count: int,
    mmr_lambda: float = MMR_LAMBDA,
) -> tuple[list[dict[str, Any]], list[str]]:
    if result_count <= 0:
        raise ValueError("Result count must be positive")
    if not 0 <= mmr_lambda <= 1:
        raise ValueError("MMR lambda must be between 0 and 1")

    available: list[dict[str, Any]] = []
    missing: list[str] = []
    normalized_vectors: dict[str, list[float]] = {}
    for candidate in candidates:
        memory_id = str(candidate.get("id", ""))
        vector = embeddings.get(memory_id)
        if vector is None:
            missing.append(memory_id)
            continue
        normalized_vectors[memory_id] = _unit_vector(validate_embedding(vector))
        available.append(dict(candidate))

    selected: list[dict[str, Any]] = []
    remaining = available
    while remaining and len(selected) < result_count:
        scored: list[tuple[float, float, str, dict[str, Any]]] = []
        for candidate in remaining:
            memory_id = str(candidate["id"])
            relevance = _as_float(candidate.get("fusion_score"))
            redundancy = 0.0
            if selected:
                redundancy = max(
                    _dot(normalized_vectors[memory_id], normalized_vectors[str(item["id"])])
                    for item in selected
                )
            mmr_score = mmr_lambda * relevance - (1 - mmr_lambda) * redundancy
            scored.append((mmr_score, relevance, memory_id, candidate))
        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        mmr_score, _, selected_id, best = scored[0]
        best["mmr_score"] = mmr_score
        selected.append(best)
        remaining = [item for item in remaining if str(item["id"]) != selected_id]

    return selected, missing


def _profile_score_weights(query_profile: str) -> dict[str, float]:
    if query_profile == "temporal":
        return {"dense": 0.35, "rrf": 0.2, "source": 0.1, "confidence": 0.1, "temporal": 0.25}
    if query_profile == "identifier":
        return {"dense": 0.35, "rrf": 0.3, "source": 0.15, "confidence": 0.1, "temporal": 0.1}
    if query_profile == "relational":
        return {"dense": 0.4, "rrf": 0.25, "source": 0.1, "confidence": 0.15, "temporal": 0.1}
    return {"dense": 0.45, "rrf": 0.25, "source": 0.1, "confidence": 0.1, "temporal": 0.1}


def _extract_candidate_groups(response: Any) -> list[tuple[str, list[dict[str, Any]]]]:
    if isinstance(response, list):
        return [("dense", [dict(item) for item in response if isinstance(item, Mapping)])]
    if not isinstance(response, Mapping):
        raise RuntimeError("Memory API returned an invalid response")

    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for key in ("dense", "lexical", "entity", "relationship", "memories", "results"):
        value = response.get(key)
        if isinstance(value, list):
            group_name = "entity" if key == "relationship" else ("dense" if key in {"memories", "results"} else key)
            groups.append((group_name, [dict(item) for item in value if isinstance(item, Mapping)]))
    if "candidate_groups" in response and isinstance(response["candidate_groups"], Mapping):
        for key, value in response["candidate_groups"].items():
            if isinstance(value, list):
                groups.append((str(key), [dict(item) for item in value if isinstance(item, Mapping)]))
    if not groups:
        raise RuntimeError("Memory API response did not include candidate memories")
    return groups


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _source_authority_score(row: Mapping[str, Any]) -> float:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
    explicit = metadata.get("source_authority") or metadata.get("authority_score")
    if explicit is not None:
        return _clamp01(_as_float(explicit, 0.5))
    if metadata.get("canonical") is True:
        return 1.0
    if row.get("source_uri") or metadata.get("source_uri") or row.get("source"):
        return 0.7
    return 0.5


def _candidate_text(row: Mapping[str, Any]) -> str:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
    parts = [
        row.get("content"),
        row.get("summary"),
        metadata.get("summary"),
        metadata.get("title"),
    ]
    return "\n".join(str(part).strip() for part in parts if str(part or "").strip())


def _score_value(row: Mapping[str, Any]) -> float:
    return _as_float(row.get("final_score"), _as_float(row.get("similarity"), 0.0))


def _min_max(values: Sequence[float]) -> list[float]:
    if not values:
        return []
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return [1.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _unit_vector(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return [0.0 for _ in values]
    return [value / norm for value in values]


def _dot(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _message_text(value: Any) -> str:
    return str(getattr(value, "text", value) or "").strip()


def _validate_memory_api_url(value: str) -> str:
    cleaned = str(value or "").strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Memory API URL must be a valid HTTP or HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("Memory API URL must not contain embedded credentials")
    return cleaned


def _safe_value(key: str, value: Any) -> Any:
    if SECRET_KEY_PATTERN.search(str(key)):
        return "[redacted]"
    if isinstance(value, Mapping):
        return {str(inner_key): _safe_value(str(inner_key), inner_value) for inner_key, inner_value in value.items()}
    if isinstance(value, list):
        return [_safe_value(key, item) for item in value]
    if isinstance(value, str) and _looks_like_secret(value):
        return "[redacted]"
    return value


def _looks_like_secret(value: str) -> bool:
    compact = value.strip()
    if len(compact) < 32:
        return False
    jwt_like = compact.count(".") == 2 and all(part for part in compact.split("."))
    high_entropy = bool(re.fullmatch(r"[A-Za-z0-9_\-+/=]{32,}", compact))
    return jwt_like or high_entropy


def _safe_memory(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): _safe_value(str(key), value)
        for key, value in row.items()
        if not str(key).startswith("_") and str(key) != "embedding"
    }


def _provenance(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = row.get("metadata") if isinstance(row.get("metadata"), Mapping) else {}
    nested_source = row.get("source") if isinstance(row.get("source"), Mapping) else {}
    return {
        "memory_id": row.get("id") or row.get("memory_id"),
        "source_uri": row.get("source_uri") or metadata.get("source_uri") or nested_source.get("source_uri"),
        "source_title": metadata.get("source_title") or metadata.get("title") or nested_source.get("source_title"),
        "source_id": row.get("source_id") or metadata.get("source_id"),
        "collection_name": row.get("collection_name") or row.get("namespace"),
        "pillar": row.get("pillar"),
    }


class LifeOSTemporalFusionRetriever(Component):
    display_name = "LifeOS Temporal Fusion Retriever"
    description = (
        "Generates local MiniLM 384D embeddings, enforces LifeOS pillar isolation, "
        "and fuses server-side memory candidates with RRF, temporal decay, and MMR."
    )
    icon = "DatabaseZap"
    name = "LifeOSTemporalFusionRetriever"

    inputs = [
        MessageInput(name="query", display_name="Query"),
        DataInput(name="route_manifest", display_name="Route Manifest"),
        DropdownInput(
            name="active_pillar",
            display_name="Active Pillar",
            options=["DEEN", "NAFS_AQL", "MAAL", "NASL_KHALQ"],
            value="MAAL",
        ),
        StrInput(name="namespace", display_name="Namespace", value="lifeos_core"),
        StrInput(name="project_id", display_name="Exact Project ID", value=""),
        StrInput(name="related_pillars", display_name="Related Pillars CSV", value=""),
        MultilineInput(name="bridge_reasons_json", display_name="Bridge Reasons JSON", value="{}"),
        FloatInput(name="router_confidence", display_name="Router Confidence", value=0.0),
        DropdownInput(
            name="query_profile",
            display_name="Query Profile",
            options=["conceptual", "identifier", "relational", "temporal"],
            value="conceptual",
        ),
        IntInput(name="result_count", display_name="Result Count", value=8),
        StrInput(name="memory_api_url", display_name="Memory API URL", value=DEFAULT_MEMORY_API_URL),
        BoolInput(name="include_sensitive", display_name="Request Sensitive Memory", value=False),
    ]

    outputs = [
        Output(name="fused_memories", display_name="Fused Memories", method="build_fused_memories"),
        Output(
            name="retrieval_diagnostics",
            display_name="Retrieval Diagnostics",
            method="build_retrieval_diagnostics",
        ),
    ]

    def _validate_runtime_inputs(self) -> dict[str, Any]:
        query_text = _message_text(self.query)
        if not query_text:
            raise ValueError("Query text is required")

        query_profile = str(self.query_profile or "").strip().lower()
        if query_profile not in QUERY_PROFILES:
            raise ValueError(f"Unknown query profile: {self.query_profile!r}")

        route_payload = model_payload(self.route_manifest)
        route = RouteManifest.model_validate(route_payload) if route_payload else None
        active_pillar = route.primary_pillar if route else self.active_pillar
        related_pillars = route.related_pillars if route else self.related_pillars
        bridge_reasons = route.bridge_reasons if route else self.bridge_reasons_json
        confidence = route.confidence if route else _as_float(self.router_confidence, default=-1.0)
        namespace = route.namespaces if route else self.namespace
        project_id = route.project_id if route else self.project_id

        if not 0 <= confidence <= 1:
            raise ValueError("Router confidence must be between 0 and 1")

        lanes, rejected_bridges = resolve_search_lanes(
            active_pillar,
            related_pillars,
            bridge_reasons,
            confidence,
            reject_invalid=True,
        )
        namespaces = validate_namespaces(namespace, project_id)
        result_count = int(self.result_count)
        if not 1 <= result_count <= MAX_RESULT_COUNT:
            raise ValueError(f"Result count must be between 1 and {MAX_RESULT_COUNT}")

        return {
            "query_text": query_text,
            "query_embedding": generate_local_embedding(query_text),
            "query_profile": query_profile,
            "router_confidence": confidence,
            "lanes": lanes,
            "rejected_bridges": rejected_bridges,
            "namespaces": namespaces,
            "project_id": project_id,
            "result_count": result_count,
            "memory_api_url": _validate_memory_api_url(self.memory_api_url),
        }

    def _request_memory_api(self, runtime: Mapping[str, Any], lane: Mapping[str, Any]) -> Any:
        # Dense retrieval request. Today the server endpoint calls
        # match_life_memories; later it can route to lifeos_hybrid_search and
        # return dense/lexical/entity candidate groups for the same RRF step.
        payload = {
            "queryEmbedding": runtime["query_embedding"],
            "queryText": runtime["query_text"],
            "queryProfile": runtime["query_profile"],
            "matchThreshold": 0.2,
            "matchCount": CANDIDATES_PER_LANE,
            "pillar": lane["pillar"],
            "collections": runtime["namespaces"],
            "includeGeneral": "lifeos_core" in runtime["namespaces"],
            "includeSensitive": bool(self.include_sensitive),
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    runtime["memory_api_url"],
                    headers={"Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Memory API request failed with status {exc.response.status_code}"
            ) from exc
        except (httpx.RequestError, ValueError) as exc:
            raise RuntimeError("Memory API request failed") from exc

    def _retrieve_lane(
        self,
        runtime: Mapping[str, Any],
        lane: Mapping[str, Any],
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
        response = self._request_memory_api(runtime, lane)
        groups = _extract_candidate_groups(response)
        lane_results: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        group_weights = QUERY_GROUP_WEIGHTS[runtime["query_profile"]]
        for group_name, rows in groups:
            filtered = [
                row
                for row in rows
                if bool(self.include_sensitive)
                or str(row.get("sensitivity", "")).lower() not in SENSITIVE_LEVELS
            ]
            weighted_lane = {
                **dict(lane),
                "group": group_name,
                "weight": float(lane["weight"]) * group_weights.get(group_name, 1.0),
            }
            lane_results.append((weighted_lane, filtered))
        return lane_results

    def _candidate_embeddings(self, candidates: Sequence[Mapping[str, Any]]) -> dict[str, list[float]]:
        embeddings: dict[str, list[float]] = {}
        for candidate in candidates[:MMR_CANDIDATE_LIMIT]:
            memory_id = str(candidate.get("id", ""))
            text = _candidate_text(candidate)
            if memory_id and text:
                embeddings[memory_id] = generate_local_embedding(text)
        return embeddings

    def _run(self) -> dict[str, Any]:
        runtime = self._validate_runtime_inputs()
        lane_results: list[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]] = []
        lane_counts: dict[str, int] = {}
        candidate_group_counts: dict[str, int] = {}

        for lane in runtime["lanes"]:
            # Pillar isolation stays per-lane. No related-pillar request is made
            # unless resolve_search_lanes accepted its bridge reason and router
            # confidence before this loop.
            results = self._retrieve_lane(runtime, lane)
            for weighted_lane, rows in results:
                lane_results.append((weighted_lane, rows))
                lane_key = f"{weighted_lane['pillar']}:{weighted_lane.get('group', 'dense')}"
                lane_counts[lane_key] = len(rows)
                candidate_group_counts[weighted_lane.get("group", "dense")] = (
                    candidate_group_counts.get(weighted_lane.get("group", "dense"), 0) + len(rows)
                )

        fused = reciprocal_rank_fusion(lane_results)
        fused, missing_temporal_timestamps = apply_temporal_decay(fused)
        ranked = calculate_fusion_scores(fused, runtime["query_profile"])
        candidate_embeddings = self._candidate_embeddings(ranked)
        selected, missing_mmr_embeddings = apply_mmr(
            ranked[:MMR_CANDIDATE_LIMIT],
            candidate_embeddings,
            runtime["result_count"],
        )

        if len(selected) < runtime["result_count"]:
            selected_ids = {str(item["id"]) for item in selected}
            for item in ranked:
                if str(item["id"]) not in selected_ids:
                    fallback = dict(item)
                    fallback["mmr_score"] = _as_float(item.get("fusion_score"))
                    selected.append(fallback)
                    selected_ids.add(str(item["id"]))
                if len(selected) >= runtime["result_count"]:
                    break

        memories: list[dict[str, Any]] = []
        for rank, item in enumerate(selected[: runtime["result_count"]], start=1):
            clean = _safe_memory(item)
            clean["memory_id"] = item.get("id")
            clean["retrieval_rank"] = rank
            clean["lane_hits"] = _safe_value("lane_hits", item.get("_lane_hits", []))
            clean["bridge_reasons"] = _safe_value("bridge_reasons", item.get("_bridge_reasons", []))
            clean["candidate_groups"] = sorted(set(item.get("_candidate_groups", [])))
            clean["provenance"] = _safe_value("provenance", _provenance(item))
            clean["scores"] = {
                "fusion": _as_float(item.get("fusion_score")),
                "rrf": _as_float(item.get("rrf_score")),
                "dense": _as_float(item.get("dense_score")),
                "temporal_decay": _as_float(item.get("temporal_decay_score")),
                "source_authority": _as_float(item.get("source_authority_score")),
                "confidence": _as_float(item.get("confidence_component")),
                "mmr": _as_float(item.get("mmr_score")),
                "original_similarity": _as_float(item.get("similarity")),
                "original_final_score": _as_float(item.get("final_score")),
            }
            memories.append(clean)

        diagnostics = {
            "component": self.name,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_dimensions": len(runtime["query_embedding"]),
            "query_profile": runtime["query_profile"],
            "active_pillar": runtime["lanes"][0]["pillar"],
            "searched_pillars": [lane["pillar"] for lane in runtime["lanes"]],
            "accepted_bridges": [
                {"pillar": lane["pillar"], "reason": lane["bridge_reason"]}
                for lane in runtime["lanes"]
                if lane["kind"] == "related"
            ],
            "rejected_bridges": runtime["rejected_bridges"],
            "namespaces": runtime["namespaces"],
            "project_id": str(runtime.get("project_id") or "").strip() or None,
            "include_sensitive_requested": bool(self.include_sensitive),
            "candidate_counts_by_lane": lane_counts,
            "candidate_counts_by_group": candidate_group_counts,
            "deduplicated_candidate_count": len(fused),
            "candidate_content_embeddings_generated": len(candidate_embeddings),
            "missing_mmr_embedding_ids": missing_mmr_embeddings,
            "missing_temporal_timestamp_count": missing_temporal_timestamps,
            "selected_count": len(memories),
            "rrf_k": RRF_K,
            "mmr_lambda": MMR_LAMBDA,
            "future_hybrid_rpc": "lifeos_hybrid_search",
        }
        self.status = (
            f"{len(memories)} memories from {len(runtime['lanes'])} pillar lane(s); "
            f"{len(fused)} fused candidate(s)"
        )
        return {"memories": memories, "diagnostics": diagnostics}

    def _cached(self) -> dict[str, Any]:
        if not hasattr(self, "_retrieval_cache") or self._retrieval_cache is None:
            self._retrieval_cache = self._run()
        return self._retrieval_cache

    def build_fused_memories(self) -> Data:
        result = self._cached()
        return Data(
            data={
                "contract": {
                    "component": self.name,
                    "embedding_model": EMBEDDING_MODEL_NAME,
                    "embedding_dimensions": EMBEDDING_DIMENSIONS,
                    "context_stage": "retrieve",
                },
                "memories": result["memories"],
                "retrieval_diagnostics": result["diagnostics"],
            }
        )

    def build_retrieval_diagnostics(self) -> Data:
        return Data(data=self._cached()["diagnostics"])
