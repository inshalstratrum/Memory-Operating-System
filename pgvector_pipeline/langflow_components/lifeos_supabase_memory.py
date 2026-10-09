from __future__ import annotations

import json
import os
import re
from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DropdownInput, IntInput, MessageInput, MultilineInput, Output, SecretStrInput, StrInput
from langflow.schema import Data
import httpx

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

PILLAR_MAP = {
    "DEEN": "deen",
    "NAFS": "nafs_aql",
    "NAFS_AQL": "nafs_aql",
    "MAAL": "maal",
    "NASL": "nasl_khalq",
    "NASL_KHALQ": "nasl_khalq",
}


def normalize_pillar(value: str) -> str:
    key = value.strip().replace("-", "_").replace("/", "_").upper()
    return PILLAR_MAP.get(key, value.strip().lower())


def get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed(text: str) -> list[float]:
    vector = get_model().encode([text], normalize_embeddings=True)[0]
    values = [float(x) for x in vector]
    if len(values) != EMBEDDING_DIMENSIONS:
        raise ValueError(f"Expected {EMBEDDING_DIMENSIONS} dimensions, got {len(values)}")
    return values


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def evaluate_protocol_gate(task_text: str, active_pillar: str, estimated_ruin_risk: float) -> dict[str, Any]:
    risky_terms = re.compile(r"\b(pay|send money|transfer|publish|email client|delete|drop|trade|invest)\b", re.I)
    flags: list[str] = []
    consent_level = "suggestion"
    blocked = False
    pillar = normalize_pillar(active_pillar)
    if estimated_ruin_risk > 0.05:
        blocked = True
        consent_level = "explicit_approval"
        flags.append("protocol_001")
    elif pillar == "maal" and risky_terms.search(task_text):
        consent_level = "explicit_approval"
        flags.append("financial_or_external_action")
    return {
        "blocked": blocked,
        "consent_level": consent_level,
        "protocol_flags": flags,
        "active_pillar": pillar,
    }


class LifeOSSupabaseMemoryRetriever(Component):
    display_name = "LifeOS Supabase Memory Retriever"
    description = "Retrieves 384-dim all-MiniLM LifeOS memories from local Supabase pgvector."
    icon = "Database"
    name = "LifeOSSupabaseMemoryRetriever"

    inputs = [
        MessageInput(name="query", display_name="Query"),
        DropdownInput(
            name="active_pillar",
            display_name="Active Pillar",
            options=["DEEN", "NAFS_AQL", "MAAL", "NASL_KHALQ"],
            value="MAAL",
        ),
        StrInput(name="collections", display_name="Collections CSV", value="lifeos_core"),
        StrInput(name="supabase_url", display_name="Supabase URL", value=os.getenv("SUPABASE_URL", "http://kong:8000")),
        SecretStrInput(name="service_role_key", display_name="Service Role Key", value=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")),
        IntInput(name="match_count", display_name="Match Count", value=8),
        BoolInput(name="include_sensitive", display_name="Include Sensitive", value=False),
    ]

    outputs = [Output(name="memories", display_name="Memories", method="retrieve")]

    def retrieve(self) -> Data:
        query_text = getattr(self.query, "text", str(self.query))
        pillar = normalize_pillar(self.active_pillar)
        collections = [item.strip() for item in self.collections.split(",") if item.strip()]
        payload = {
            "query_embedding": vector_literal(embed(query_text)),
            "match_threshold": 0.2,
            "match_count": self.match_count,
            "filter_pillar": pillar,
            "filter_collections": collections,
            "include_general": True,
            "include_sensitive": self.include_sensitive,
        }
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/rpc/match_life_memories"
        with httpx.Client(timeout=30) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        rows = response.json()
        return Data(data={"memories": rows, "active_pillar": pillar, "collections": collections})


class LifeOSAuditLogger(Component):
    display_name = "LifeOS Audit Logger"
    description = "Writes append-only Protocol/Consent events to local Supabase."
    icon = "ShieldCheck"
    name = "LifeOSAuditLogger"

    inputs = [
        StrInput(name="event_type", display_name="Event Type", value="langflow.run"),
        DropdownInput(
            name="consent_level",
            display_name="Consent Level",
            options=["suggestion", "draft", "low_risk_autopilot", "explicit_approval"],
            value="suggestion",
        ),
        StrInput(name="protocol_flags", display_name="Protocol Flags CSV", value=""),
        MultilineInput(name="payload_json", display_name="Payload JSON", value="{}"),
        StrInput(name="supabase_url", display_name="Supabase URL", value=os.getenv("SUPABASE_URL", "http://kong:8000")),
        SecretStrInput(name="service_role_key", display_name="Service Role Key", value=os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")),
    ]

    outputs = [Output(name="result", display_name="Result", method="log")]

    def log(self) -> Data:
        try:
            payload: dict[str, Any] = json.loads(self.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {"raw": self.payload_json}
        flags = [item.strip() for item in self.protocol_flags.split(",") if item.strip()]
        body = {
            "event_type": self.event_type,
            "consent_level": self.consent_level,
            "protocol_flags": flags,
            "actor": "langflow",
            "source": "lifeos_canvas",
            "payload": payload,
            "payload_hash": "pending",
        }
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        url = f"{self.supabase_url.rstrip('/')}/rest/v1/life_audit_log"
        with httpx.Client(timeout=30) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
        return Data(data={"logged": True, "rows": response.json()})


class LifeOSProtocolGate(Component):
    display_name = "LifeOS Protocol 001 Gate"
    description = "Blocks ruin-risk and escalates financial/external actions to explicit approval."
    icon = "OctagonAlert"
    name = "LifeOSProtocolGate"

    inputs = [
        MessageInput(name="task", display_name="Task"),
        DropdownInput(
            name="active_pillar",
            display_name="Active Pillar",
            options=["DEEN", "NAFS_AQL", "MAAL", "NASL_KHALQ"],
            value="MAAL",
        ),
        StrInput(name="estimated_ruin_risk", display_name="Estimated Ruin Risk", value="0.0"),
    ]

    outputs = [Output(name="gate", display_name="Gate", method="gate")]

    def gate(self) -> Data:
        task_text = getattr(self.task, "text", str(self.task))
        risk = float(self.estimated_ruin_risk or 0)
        return Data(data=evaluate_protocol_gate(task_text, self.active_pillar, risk))
