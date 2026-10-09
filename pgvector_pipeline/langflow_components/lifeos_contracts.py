from __future__ import annotations

"""Typed contracts and safety helpers shared by Shali Brain v3 Phase 2 nodes."""

import hashlib
import json
import math
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Pillar = Literal["deen", "nafs_aql", "maal", "nasl_khalq"]
Sensitivity = Literal["public", "internal", "private", "sensitive", "secret"]
Complexity = Literal["simple", "standard", "complex", "deep"]
Decision = Literal["allow", "requires_approval", "block"]
ToolStatus = Literal["success", "no_op", "blocked", "failed", "not_executed"]
Verdict = Literal["accept", "reject", "repair"]

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

NAMESPACE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,254}$")
SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|authorization|bearer|credential|jwt|password|pin|secret|service[_-]?role|token)",
    re.IGNORECASE,
)
CHAIN_OF_THOUGHT_KEY_PATTERN = re.compile(
    r"(chain[_ -]?of[_ -]?thought|hidden[_ -]?reasoning|internal[_ -]?reasoning|scratchpad|private[_ -]?thoughts?)",
    re.IGNORECASE,
)
SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?i)\b(?:api[_ -]?key|password|service[_ -]?role|access[_ -]?token|secret|master[_ -]?pin)\b"
    r"\s*[:=]\s*\S+"
)
HIGH_ENTROPY_PATTERN = re.compile(r"^[A-Za-z0-9_\-+/=]{32,}$")


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RouteManifest(ContractModel):
    contract_version: str = "shali.route.v3"
    query: str = Field(min_length=1, max_length=12000)
    primary_pillar: Pillar
    related_pillars: list[Pillar] = Field(default_factory=list, max_length=2)
    bridge_reasons: dict[str, str] = Field(default_factory=dict)
    namespaces: list[str] = Field(default_factory=lambda: ["lifeos_core"], min_length=1)
    project_id: str | None = None
    sensitivity: Sensitivity = "internal"
    task_class: str = Field(default="conversation", min_length=1, max_length=80)
    complexity: Complexity = "standard"
    tool_needs: list[str] = Field(default_factory=list, max_length=16)
    confidence: float = Field(ge=0.0, le=1.0)
    routing_basis: list[str] = Field(default_factory=list, max_length=16)

    @field_validator("related_pillars")
    @classmethod
    def unique_related_pillars(cls, value: list[Pillar]) -> list[Pillar]:
        if len(value) != len(set(value)):
            raise ValueError("Related pillars must be unique")
        return value

    @field_validator("namespaces")
    @classmethod
    def valid_namespaces(cls, value: list[str]) -> list[str]:
        unique: list[str] = []
        for namespace in value:
            if not NAMESPACE_PATTERN.fullmatch(namespace):
                raise ValueError(f"Invalid namespace: {namespace!r}")
            if namespace not in unique:
                unique.append(namespace)
        if "lifeos_core" not in unique:
            unique.append("lifeos_core")
        return unique

    @model_validator(mode="after")
    def enforce_route_isolation(self) -> "RouteManifest":
        if self.primary_pillar in self.related_pillars:
            raise ValueError("Primary pillar cannot also be a related pillar")
        if self.related_pillars and self.confidence < 0.75:
            raise ValueError("Related pillars require router confidence of at least 0.75")
        for pillar in self.related_pillars:
            if not self.bridge_reasons.get(pillar, "").strip():
                raise ValueError(f"Related pillar {pillar!r} requires a bridge reason")
        validate_namespace_access(self.namespaces, self.project_id)
        return self


class PlanStep(ContractModel):
    step_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
    title: str = Field(min_length=1, max_length=240)
    instruction: str = Field(min_length=1, max_length=4000)
    tool_id: str = Field(default="internal.context_synthesis", min_length=1, max_length=160)
    operation_class: str = Field(default="internal", min_length=1, max_length=80)
    namespaces: list[str] = Field(default_factory=list, max_length=16)
    expected_evidence: list[str] = Field(default_factory=list, max_length=32)
    estimated_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    completion_criteria: list[str] = Field(default_factory=list, min_length=1, max_length=16)
    payload: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(ContractModel):
    contract_version: str = "shali.plan.v3"
    plan_id: str = Field(min_length=1, max_length=120)
    route: RouteManifest
    objective: str = Field(min_length=1, max_length=12000)
    steps: list[PlanStep] = Field(min_length=1, max_length=32)
    tool_requirements: list[str] = Field(default_factory=list, max_length=32)
    max_repair_cycles: int = Field(default=2, ge=0, le=3)
    max_tool_calls: int = Field(default=8, ge=0, le=8)
    max_model_tokens: int = Field(default=12000, ge=256, le=30000)
    max_wall_time_seconds: int = Field(default=120, ge=1, le=300)
    completion_criteria: list[str] = Field(default_factory=list, min_length=1, max_length=24)
    candidate_plan_count: int = Field(default=1, ge=1, le=2)

    @model_validator(mode="after")
    def enforce_plan_scope(self) -> "ExecutionPlan":
        step_ids = [step.step_id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("Plan step IDs must be unique")
        return self


class ActionRequest(ContractModel):
    contract_version: str = "shali.action.v3"
    plan_id: str
    step_id: str
    action_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    tool_id: str
    operation_class: str
    namespaces: list[str] = Field(default_factory=list)
    effective_risk: float = Field(ge=0.0, le=1.0)
    consent_level: Literal[
        "suggestion",
        "draft",
        "low_risk_autopilot",
        "explicit_approval",
    ] = "suggestion"
    decision: Decision
    reasons: list[str] = Field(default_factory=list)
    expires_in_seconds: int = Field(default=120, ge=1, le=120)


class ExecutionPermit(ContractModel):
    contract_version: str = "shali.permit.v3"
    permit_id: str
    action_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    approved: bool = False
    verified_by_gateway: bool = False
    expires_at: datetime
    consumed: bool = False
    subject: str | None = None

    @field_validator("expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class ToolResult(ContractModel):
    contract_version: str = "shali.tool_result.v3"
    plan_id: str
    step_id: str
    tool_id: str
    status: ToolStatus
    output: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    namespaces: list[str] = Field(default_factory=list)
    pillar: Pillar
    mutation_performed: bool = False
    external_effect: bool = False
    result_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    error_code: str | None = None


class CriticVerdict(ContractModel):
    contract_version: str = "shali.critic.v3"
    critic: Literal["evidence", "policy"]
    verdict: Verdict
    accepted_step_ids: list[str] = Field(default_factory=list)
    rejected_step_ids: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    repair_instructions: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    policy_flags: list[str] = Field(default_factory=list)


class MemoryCandidate(ContractModel):
    contract_version: str = "shali.memory_candidate.v3"
    candidate_id: str
    status: Literal["draft"] = "draft"
    content: str = Field(min_length=1, max_length=12000)
    pillar: Pillar
    namespace: str
    memory_kind: Literal[
        "short_term",
        "task",
        "agent_trace",
        "episodic",
        "semantic",
        "persona",
        "canonical",
    ] = "episodic"
    sensitivity: Sensitivity = "internal"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    consent_level: Literal[
        "suggestion",
        "draft",
        "low_risk_autopilot",
        "explicit_approval",
    ] = "draft"
    canonical_write_allowed: Literal[False] = False

    @field_validator("namespace")
    @classmethod
    def valid_namespace(cls, value: str) -> str:
        if not NAMESPACE_PATTERN.fullmatch(value):
            raise ValueError(f"Invalid namespace: {value!r}")
        return value

    @field_validator("content")
    @classmethod
    def no_chain_of_thought(cls, value: str) -> str:
        sanitized = sanitize_text(value)
        if not sanitized:
            raise ValueError("Memory candidate content is empty after sanitization")
        return sanitized


def normalize_pillar(value: str) -> Pillar:
    key = str(value or "").strip().replace("-", "_").upper()
    pillar = PILLAR_ALIASES.get(key, key.lower())
    if pillar not in VALID_PILLARS:
        raise ValueError(f"Unknown LifeOS pillar: {value!r}")
    return pillar  # type: ignore[return-value]


def validate_namespace_access(namespaces: list[str], project_id: str | None) -> None:
    client_namespaces = [item for item in namespaces if item.startswith("client_")]
    normalized_project = str(project_id or "").strip()
    if client_namespaces and not normalized_project:
        raise ValueError("Client namespaces require an exact project ID")
    if not client_namespaces:
        return
    expected = (
        normalized_project
        if normalized_project.startswith("client_")
        else f"client_{normalized_project}"
    )
    if any(namespace != expected for namespace in client_namespaces):
        raise ValueError("Cross-client namespace access denied")


def model_payload(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if hasattr(value, "data"):
        return getattr(value, "data")
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return value


def canonical_json(value: Any) -> str:
    payload = model_payload(value)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sanitize_text(value: Any, *, max_length: int = 12000) -> str:
    text = str(value or "")
    text = SENSITIVE_TEXT_PATTERN.sub("[redacted]", text)
    lines = [
        line
        for line in text.splitlines()
        if not CHAIN_OF_THOUGHT_KEY_PATTERN.search(line)
    ]
    text = "\n".join(lines)
    if _looks_like_secret(text.strip()):
        return "[redacted]"
    return text[:max_length].strip()


def sanitize_payload(value: Any, *, max_text_length: int = 12000) -> Any:
    payload = model_payload(value)
    if isinstance(payload, Mapping):
        safe: dict[str, Any] = {}
        for key, item in payload.items():
            key_text = str(key)
            if CHAIN_OF_THOUGHT_KEY_PATTERN.search(key_text):
                continue
            if SECRET_KEY_PATTERN.search(key_text):
                safe[key_text] = "[redacted]"
            else:
                safe[key_text] = sanitize_payload(item, max_text_length=max_text_length)
        return safe
    if isinstance(payload, list):
        return [sanitize_payload(item, max_text_length=max_text_length) for item in payload]
    if isinstance(payload, tuple):
        return [sanitize_payload(item, max_text_length=max_text_length) for item in payload]
    if isinstance(payload, str):
        return sanitize_text(payload, max_length=max_text_length)
    if isinstance(payload, float) and not math.isfinite(payload):
        return None
    return payload


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _looks_like_secret(value: str) -> bool:
    if len(value) < 32:
        return False
    jwt_like = value.count(".") == 2 and all(part for part in value.split("."))
    return jwt_like or bool(HIGH_ENTROPY_PATTERN.fullmatch(value))
