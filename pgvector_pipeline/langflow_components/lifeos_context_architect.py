from __future__ import annotations

"""Minimum-necessary context assembly for the Shali Brain v3 planner."""

import json
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, IntInput, MultilineInput, Output
from langflow.schema import Data

try:
    from lifeos_contracts import RouteManifest, model_payload, sanitize_payload, sanitize_text
except ImportError:
    from .lifeos_contracts import RouteManifest, model_payload, sanitize_payload, sanitize_text

DEFAULT_PILLAR_RULES = {
    "deen": [
        "Use approved, attributable sources for religious claims.",
        "Do not invent rulings or present uncertainty as certainty.",
        "Preserve Akhirah awareness and the user's sovereignty.",
    ],
    "nafs_aql": [
        "Support capacity, learning, and character without diagnosing.",
        "Mark medical or mental-health uncertainty and avoid clinical claims.",
        "Prefer sustainable steps that protect sleep, health, and cognition.",
    ],
    "maal": [
        "Treat wealth and work as stewardship; avoid ruin-risk actions.",
        "Financial, external, or client-facing actions require explicit approval.",
        "Do not execute transactions or commitments in Phase 2.",
    ],
    "nasl_khalq": [
        "Protect rights, consent, privacy, and relationship context.",
        "Communication outputs are drafts unless explicitly approved elsewhere.",
        "Do not send messages or make commitments in Phase 2.",
    ],
}

SENSITIVITY_ORDER = {
    "public": 0,
    "internal": 1,
    "private": 2,
    "sensitive": 3,
    "secret": 4,
}


def build_context_package(
    route_value: Any,
    retrieval_value: Any,
    recent_context_value: Any = None,
    pillar_rules_value: Any = None,
    *,
    max_memories: int = 8,
    max_context_characters: int = 16000,
    cloud_context_allowed: bool = True,
) -> dict[str, Any]:
    route = RouteManifest.model_validate(model_payload(route_value))
    retrieval = model_payload(retrieval_value) or {}
    recent_context = sanitize_payload(model_payload(recent_context_value) or [])
    custom_rules = _parse_rules(pillar_rules_value)

    allowed_pillars = {route.primary_pillar, *route.related_pillars}
    allowed_namespaces = set(route.namespaces)
    raw_memories = retrieval.get("memories", []) if isinstance(retrieval, dict) else []
    memories: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    provenance: list[dict[str, Any]] = []

    for raw in raw_memories:
        if not isinstance(raw, dict):
            rejected.append({"memory_id": "", "reason": "invalid_memory_shape"})
            continue
        memory_id = str(raw.get("memory_id") or raw.get("id") or "")
        pillar = str(raw.get("pillar") or "").lower()
        namespace = str(raw.get("collection_name") or raw.get("namespace") or "lifeos_core")
        if pillar and pillar not in allowed_pillars:
            rejected.append({"memory_id": memory_id, "reason": "pillar_isolation"})
            continue
        if namespace not in allowed_namespaces:
            rejected.append({"memory_id": memory_id, "reason": "namespace_isolation"})
            continue

        safe = sanitize_payload(raw)
        safe.pop("embedding", None)
        safe.pop("scores", None)
        safe["memory_id"] = memory_id
        memories.append(safe)
        source = safe.get("provenance") if isinstance(safe.get("provenance"), dict) else {}
        provenance.append(
            {
                "memory_id": memory_id,
                "pillar": pillar or route.primary_pillar,
                "namespace": namespace,
                "source_uri": source.get("source_uri"),
                "source_title": source.get("source_title"),
            }
        )
        if len(memories) >= max_memories:
            break

    rules = {
        pillar: custom_rules.get(pillar, DEFAULT_PILLAR_RULES[pillar])
        for pillar in [route.primary_pillar, *route.related_pillars]
    }
    local_package = {
        "contract": "shali.context.v3",
        "route": route.model_dump(mode="json"),
        "pillar_rules": rules,
        "memories": memories,
        "recent_context": recent_context,
        "provenance": provenance,
        "constraints": {
            "protocol_001_risk_threshold": 0.05,
            "no_raw_chain_of_thought": True,
            "external_actions_enabled": False,
            "canonical_memory_write_enabled": False,
        },
        "diagnostics": {
            "accepted_memory_count": len(memories),
            "rejected_memories": rejected,
            "max_context_characters": max_context_characters,
        },
    }
    local_package = _bound_package(local_package, max_context_characters)

    cloud_package = _cloud_safe_context(local_package, cloud_context_allowed)
    return {
        "context_package": local_package,
        "sanitized_cloud_context": cloud_package,
    }


def _parse_rules(value: Any) -> dict[str, list[str]]:
    payload = model_payload(value)
    if payload is None or payload == "":
        return {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Pillar rules must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Pillar rules must be a JSON object")

    rules: dict[str, list[str]] = {}
    for pillar, raw_rules in payload.items():
        if pillar not in DEFAULT_PILLAR_RULES:
            continue
        if isinstance(raw_rules, list):
            rules[pillar] = [sanitize_text(item, max_length=1000) for item in raw_rules if str(item).strip()]
    return rules


def _bound_package(package: dict[str, Any], max_characters: int) -> dict[str, Any]:
    encoded = json.dumps(package, ensure_ascii=True, default=str)
    if len(encoded) <= max_characters:
        return package

    bounded = dict(package)
    bounded["recent_context"] = []
    memories = list(bounded.get("memories", []))
    while memories:
        bounded["memories"] = memories
        encoded = json.dumps(bounded, ensure_ascii=True, default=str)
        if len(encoded) <= max_characters:
            break
        memories.pop()
    bounded["diagnostics"]["truncated_for_budget"] = True
    bounded["diagnostics"]["accepted_memory_count"] = len(memories)
    return bounded


def _cloud_safe_context(package: dict[str, Any], allowed: bool) -> dict[str, Any]:
    if not allowed:
        return {
            "contract": "shali.cloud_context.v3",
            "cloud_allowed": False,
            "reason": "cloud_context_disabled",
        }

    route = dict(package["route"])
    if SENSITIVITY_ORDER.get(str(route.get("sensitivity")), 4) >= SENSITIVITY_ORDER["sensitive"]:
        route["query"] = "[sensitive query withheld from cloud]"

    memories = []
    for memory in package.get("memories", []):
        sensitivity = str(memory.get("sensitivity", "internal")).lower()
        if SENSITIVITY_ORDER.get(sensitivity, 4) >= SENSITIVITY_ORDER["sensitive"]:
            continue
        memories.append(memory)

    return sanitize_payload(
        {
            "contract": "shali.cloud_context.v3",
            "cloud_allowed": True,
            "provider_requirements": {
                "zdr": True,
                "data_collection": "deny",
                "parameter_enforcement": True,
            },
            "route": route,
            "pillar_rules": package.get("pillar_rules", {}),
            "memories": memories,
            "provenance": [
                item
                for item in package.get("provenance", [])
                if item.get("memory_id") in {memory.get("memory_id") for memory in memories}
            ],
            "constraints": package.get("constraints", {}),
        }
    )


class LifeOSContextArchitect(Component):
    display_name = "LifeOS Context Architect"
    description = "Builds minimum-necessary local and cloud-sanitized context with provenance."
    icon = "Filter"
    name = "LifeOSContextArchitect"

    inputs = [
        DataInput(name="route_manifest", display_name="Route Manifest"),
        DataInput(name="retrieved_memories", display_name="Retrieved Memories"),
        DataInput(name="recent_context", display_name="Recent Context"),
        MultilineInput(name="pillar_rules_json", display_name="Pillar Rules JSON", value="{}"),
        IntInput(name="max_memories", display_name="Max Memories", value=8),
        IntInput(name="max_context_characters", display_name="Max Context Characters", value=16000),
        BoolInput(name="cloud_context_allowed", display_name="Allow Sanitized Cloud Context", value=True),
    ]

    outputs = [
        Output(name="context_package", display_name="Context Package", method="build_local_context"),
        Output(
            name="sanitized_cloud_context",
            display_name="Sanitized Cloud Context",
            method="build_cloud_context",
        ),
    ]

    def _build(self) -> dict[str, Any]:
        if not hasattr(self, "_context_cache") or self._context_cache is None:
            self._context_cache = build_context_package(
                self.route_manifest,
                self.retrieved_memories,
                self.recent_context,
                self.pillar_rules_json,
                max_memories=max(1, min(int(self.max_memories), 20)),
                max_context_characters=max(2000, min(int(self.max_context_characters), 30000)),
                cloud_context_allowed=bool(self.cloud_context_allowed),
            )
        return self._context_cache

    def build_local_context(self) -> Data:
        payload = self._build()["context_package"]
        self.status = f"{len(payload.get('memories', []))} memories in context"
        return Data(data=payload)

    def build_cloud_context(self) -> Data:
        return Data(data=self._build()["sanitized_cloud_context"])
