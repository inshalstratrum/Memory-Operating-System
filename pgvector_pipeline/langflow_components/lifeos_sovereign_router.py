from __future__ import annotations

"""Deterministic local router for Shali Brain v3's four LifeOS pillars."""

import re
from typing import Any

from langflow.custom import Component
from langflow.io import MessageInput, Output, StrInput
from langflow.schema import Data
from langflow.schema.message import Message

try:
    from lifeos_contracts import RouteManifest, normalize_pillar, sanitize_text
except ImportError:
    from .lifeos_contracts import RouteManifest, normalize_pillar, sanitize_text

PILLAR_TERMS = {
    "deen": {
        "allah",
        "akhirah",
        "adhkar",
        "deen",
        "dua",
        "fajr",
        "faith",
        "halal",
        "haram",
        "ibadah",
        "islam",
        "prayer",
        "quran",
        "salah",
        "sadaqah",
        "taqwa",
        "zakat",
    },
    "nafs_aql": {
        "aql",
        "book",
        "character",
        "exercise",
        "fitness",
        "focus",
        "habit",
        "health",
        "learn",
        "mind",
        "nafs",
        "nutrition",
        "reason",
        "research",
        "sleep",
        "study",
        "workout",
    },
    "maal": {
        "agency",
        "animation",
        "asset",
        "budget",
        "business",
        "client",
        "editing",
        "finance",
        "freelance",
        "invoice",
        "maal",
        "money",
        "proposal",
        "restaurant",
        "revenue",
        "upwork",
        "video",
        "work",
    },
    "nasl_khalq": {
        "client",
        "community",
        "family",
        "friend",
        "khalq",
        "leadership",
        "message",
        "nasl",
        "network",
        "parent",
        "relationship",
        "reply",
        "team",
        "tone",
        "ummah",
    },
}

SENSITIVE_TERMS = {
    "password",
    "pin",
    "secret",
    "service role",
    "api key",
    "credential",
    "private key",
    "access token",
}
EXTERNAL_ACTION_TERMS = {
    "send",
    "publish",
    "post",
    "email",
    "transfer",
    "buy",
    "sell",
    "delete",
    "pay",
}


def classify_route(
    query: str,
    namespace: str = "lifeos_core",
    project_id: str | None = None,
) -> RouteManifest:
    clean_query = sanitize_text(query)
    if not clean_query:
        raise ValueError("Router query is empty after sanitization")

    lowered = clean_query.lower()
    words = set(re.findall(r"[a-z0-9_]+", lowered))
    scores: dict[str, int] = {}
    matches: dict[str, list[str]] = {}
    for pillar, terms in PILLAR_TERMS.items():
        hits = sorted(term for term in terms if term in words or (" " in term and term in lowered))
        matches[pillar] = hits
        scores[pillar] = len(hits)

    ranked = sorted(scores, key=lambda item: (-scores[item], item))
    primary = ranked[0] if scores[ranked[0]] > 0 else "nafs_aql"
    top_score = scores[primary]
    second_score = scores[ranked[1]] if len(ranked) > 1 else 0
    confidence = (
        min(0.98, 0.55 + 0.1 * top_score + 0.1 * second_score)
        if top_score
        else 0.52
    )

    related: list[str] = []
    bridge_reasons: dict[str, str] = {}
    if confidence >= 0.75:
        for pillar in ranked[1:]:
            if scores[pillar] <= 0 or len(related) >= 2:
                continue
            related.append(pillar)
            bridge_reasons[pillar] = (
                f"Prompt contains {pillar} routing signals: {', '.join(matches[pillar][:4])}"
            )

    namespaces = [item.strip() for item in str(namespace or "lifeos_core").split(",") if item.strip()]
    if not namespaces:
        namespaces = ["lifeos_core"]

    sensitivity = "secret" if any(term in lowered for term in SENSITIVE_TERMS) else "internal"
    task_class = _task_class(lowered)
    complexity = _complexity(clean_query, lowered)
    tool_needs = _tool_needs(lowered)
    basis = [f"{pillar}:{','.join(matches[pillar][:4])}" for pillar in ranked if matches[pillar]]
    if not basis:
        basis = ["fallback:nafs_aql"]

    return RouteManifest(
        query=clean_query,
        primary_pillar=normalize_pillar(primary),
        related_pillars=[normalize_pillar(item) for item in related],
        bridge_reasons=bridge_reasons,
        namespaces=namespaces,
        project_id=str(project_id or "").strip() or None,
        sensitivity=sensitivity,
        task_class=task_class,
        complexity=complexity,
        tool_needs=tool_needs,
        confidence=confidence,
        routing_basis=basis,
    )


def _task_class(lowered: str) -> str:
    if any(term in lowered for term in EXTERNAL_ACTION_TERMS):
        return "action_request"
    if any(term in lowered for term in ("plan", "roadmap", "steps", "schedule")):
        return "planning"
    if any(term in lowered for term in ("draft", "write", "reply", "proposal")):
        return "drafting"
    if any(term in lowered for term in ("find", "recall", "remember", "retrieve", "search")):
        return "retrieval"
    if any(term in lowered for term in ("analyze", "compare", "evaluate", "review")):
        return "analysis"
    return "conversation"


def _complexity(query: str, lowered: str) -> str:
    if "deep mode" in lowered or len(query) > 4000:
        return "deep"
    if len(query) > 1400 or lowered.count("\n") >= 8:
        return "complex"
    if len(query) < 180 and not any(term in lowered for term in ("plan", "analyze", "compare")):
        return "simple"
    return "standard"


def _tool_needs(lowered: str) -> list[str]:
    needs: list[str] = []
    if any(term in lowered for term in ("calendar", "schedule", "appointment")):
        needs.append("calendar.read")
    if any(term in lowered for term in ("browse", "website", "web search", "latest")):
        needs.append("web.read")
    if any(term in lowered for term in ("run python", "calculate with python", "analyze file")):
        needs.append("python.analyze")
    if any(term in lowered for term in EXTERNAL_ACTION_TERMS):
        needs.append("external.action")
    return needs


def _message_text(value: Any) -> str:
    return str(getattr(value, "text", value) or "").strip()


class LifeOSSovereignRouter(Component):
    display_name = "LifeOS Sovereign Router"
    description = "Locally emits a typed four-pillar RouteManifest with controlled bridges."
    icon = "Route"
    name = "LifeOSSovereignRouter"

    inputs = [
        MessageInput(name="user_input", display_name="User Input"),
        StrInput(name="namespace", display_name="Namespace", value="lifeos_core"),
        StrInput(name="project_id", display_name="Exact Project ID", value=""),
    ]

    outputs = [
        Output(name="route_manifest", display_name="Route Manifest", method="build_route"),
        Output(name="clean_query", display_name="Clean Query", method="build_clean_query"),
    ]

    def _route(self) -> RouteManifest:
        if not hasattr(self, "_route_cache") or self._route_cache is None:
            self._route_cache = classify_route(
                _message_text(self.user_input),
                namespace=self.namespace,
                project_id=self.project_id,
            )
        return self._route_cache

    def build_route(self) -> Data:
        route = self._route()
        self.status = (
            f"{route.primary_pillar}; confidence={route.confidence:.2f}; "
            f"bridges={len(route.related_pillars)}"
        )
        return Data(data=route.model_dump(mode="json"))

    def build_clean_query(self) -> Message:
        return Message(text=self._route().query)
