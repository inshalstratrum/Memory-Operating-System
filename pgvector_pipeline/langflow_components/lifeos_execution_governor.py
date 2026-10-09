from __future__ import annotations

"""Deterministic Protocol 000-003 governance for Shali Brain v3."""

import json
import re
from datetime import timezone
from typing import Any

from langflow.custom import Component
from langflow.io import DataInput, MultilineInput, Output
from langflow.schema import Data

try:
    from lifeos_contracts import (
        ActionRequest,
        ExecutionPermit,
        ExecutionPlan,
        RouteManifest,
        canonical_json,
        model_payload,
        sanitize_payload,
        sha256_hex,
        utc_now,
        validate_namespace_access,
    )
except ImportError:
    from .lifeos_contracts import (
        ActionRequest,
        ExecutionPermit,
        ExecutionPlan,
        RouteManifest,
        canonical_json,
        model_payload,
        sanitize_payload,
        sha256_hex,
        utc_now,
        validate_namespace_access,
    )

RUIN_RISK_THRESHOLD = 0.05
APPROVAL_OPERATION_CLASSES = {
    "external",
    "external_read",
    "financial",
    "destructive",
    "client_facing",
}
POLICY_RISK_FLOORS = {
    "internal": 0.0,
    "draft": 0.0,
    "local_compute": 0.04,
    "external_read": 0.06,
    "external": 0.15,
    "client_facing": 0.15,
    "financial": 0.25,
    "destructive": 0.5,
    "unknown": 1.0,
}
SECRET_EXFILTRATION_PATTERN = re.compile(
    r"(?i)\b(?:send|upload|publish|post|email|transmit|expose|return)\b.{0,80}"
    r"\b(?:api[_ -]?key|password|private[_ -]?key|service[_ -]?role|secret|token|master[_ -]?pin)\b"
)

DEFAULT_TOOL_CATALOG = {
    "internal.context_synthesis": {
        "risk_floor": 0.0,
        "operation_class": "internal",
        "allowed_pillars": ["deen", "nafs_aql", "maal", "nasl_khalq"],
        "allowed_namespaces": ["*"],
        "phase2_stub_allowed": True,
    },
    "internal.response_draft": {
        "risk_floor": 0.0,
        "operation_class": "draft",
        "allowed_pillars": ["deen", "nafs_aql", "maal", "nasl_khalq"],
        "allowed_namespaces": ["*"],
        "phase2_stub_allowed": True,
    },
    "internal.noop": {
        "risk_floor": 0.0,
        "operation_class": "internal",
        "allowed_pillars": ["deen", "nafs_aql", "maal", "nasl_khalq"],
        "allowed_namespaces": ["*"],
        "phase2_stub_allowed": True,
    },
}


def govern_execution(
    route_value: Any,
    plan_value: Any,
    tool_catalog_value: Any = None,
    permit_value: Any = None,
) -> dict[str, Any]:
    route = RouteManifest.model_validate(model_payload(route_value))
    plan = ExecutionPlan.model_validate(model_payload(plan_value))
    if plan.route != route:
        raise ValueError("Execution plan route does not match the supplied RouteManifest")

    catalog = _parse_tool_catalog(tool_catalog_value)
    permit, permit_error = _parse_permit(permit_value)
    decisions: list[dict[str, Any]] = []
    approved_steps: list[dict[str, Any]] = []
    approval_requests: list[dict[str, Any]] = []
    blocked_steps: list[str] = []

    for step in plan.steps:
        action_hash = sha256_hex(step.model_dump(mode="json"))
        tool = catalog.get(step.tool_id)
        reasons: list[str] = []
        flags: list[str] = []
        decision = "allow"
        effective_risk = 1.0

        if tool is None:
            decision = "block"
            reasons.append("Unknown tool is not present in the authoritative catalog")
            flags.append("unknown_tool")
        else:
            operation_class = str(tool.get("operation_class") or step.operation_class or "unknown")
            tool_risk_floor = _risk(tool.get("risk_floor"), default=1.0)
            policy_floor = deterministic_policy_floor(step.model_dump(mode="json"), operation_class)
            effective_risk = max(step.estimated_risk, tool_risk_floor, policy_floor)

            absolute_flags = _absolute_policy_blocks(route, step.model_dump(mode="json"), tool)
            if permit_error:
                absolute_flags.append("permit_tampering")
            if permit is not None and permit.action_hash != action_hash:
                absolute_flags.append("permit_tampering")

            if absolute_flags:
                decision = "block"
                flags.extend(sorted(set(absolute_flags)))
                reasons.extend(_flag_reason(flag) for flag in sorted(set(absolute_flags)))
            elif (
                effective_risk > RUIN_RISK_THRESHOLD
                or operation_class in APPROVAL_OPERATION_CLASSES
            ):
                if _permit_allows(permit, action_hash):
                    decision = "allow"
                    reasons.append("Exact action has a gateway-verified, unexpired permit")
                    flags.append("explicit_approval_verified")
                else:
                    decision = "requires_approval"
                    reasons.append(
                        f"Protocol 001 requires approval because effective risk "
                        f"{effective_risk:.4f} exceeds {RUIN_RISK_THRESHOLD:.2f} "
                        f"or the operation class is approval-only"
                    )
                    flags.append("protocol_001")

        consent_level = (
            "explicit_approval"
            if decision in {"requires_approval", "block"} or effective_risk > RUIN_RISK_THRESHOLD
            else ("draft" if step.operation_class == "draft" else "low_risk_autopilot")
        )
        request = ActionRequest(
            plan_id=plan.plan_id,
            step_id=step.step_id,
            action_hash=action_hash,
            tool_id=step.tool_id,
            operation_class=step.operation_class,
            namespaces=step.namespaces,
            effective_risk=min(1.0, effective_risk),
            consent_level=consent_level,
            decision=decision,
            reasons=reasons,
            expires_in_seconds=120,
        )
        decision_payload = {
            **request.model_dump(mode="json"),
            "policy_flags": flags,
            "approved_for_stub_execution": decision == "allow",
        }
        decisions.append(decision_payload)
        if decision == "allow":
            approved_steps.append(step.model_dump(mode="json"))
        elif decision == "requires_approval":
            approval_requests.append(request.model_dump(mode="json"))
        else:
            blocked_steps.append(step.step_id)

    overall = (
        "block"
        if blocked_steps
        else ("requires_approval" if approval_requests else "allow")
    )
    decision_document = {
        "contract": "shali.governor_decision.v3",
        "plan_id": plan.plan_id,
        "overall_decision": overall,
        "protocol_001_threshold": RUIN_RISK_THRESHOLD,
        "step_decisions": decisions,
        "blocked_step_ids": blocked_steps,
        "approval_step_ids": [item["step_id"] for item in approval_requests],
        "approved_step_ids": [item["step_id"] for item in approved_steps],
        "permit_consumed": False,
        "permit_verification_note": (
            "The governor never verifies PINs or signatures. It accepts only the "
            "verified_by_gateway marker and leaves atomic permit consumption to the gateway."
        ),
    }
    audit_payload = sanitize_payload(
        {
            "event_type": "orchestration.governed",
            "actor": "langflow",
            "source": "lifeos_execution_governor",
            "plan_id": plan.plan_id,
            "route": {
                "primary_pillar": route.primary_pillar,
                "related_pillars": route.related_pillars,
                "namespaces": route.namespaces,
                "project_id": route.project_id,
                "sensitivity": route.sensitivity,
            },
            "decision": decision_document,
        }
    )
    audit_payload["payload_hash"] = sha256_hex(audit_payload)

    return {
        "approved_plan": {
            "contract": "shali.approved_plan.v3",
            "plan_id": plan.plan_id,
            "route": route.model_dump(mode="json"),
            "steps": approved_steps,
            "budget": {
                "max_tool_calls": plan.max_tool_calls,
                "max_wall_time_seconds": plan.max_wall_time_seconds,
                "max_model_tokens": plan.max_model_tokens,
            },
        },
        "decision": decision_document,
        "approval_request": {
            "contract": "shali.approval_requests.v3",
            "requests": approval_requests,
        },
        "audit_event": audit_payload,
    }


def deterministic_policy_floor(step: dict[str, Any], operation_class: str | None = None) -> float:
    operation = str(operation_class or step.get("operation_class") or "unknown")
    floor = POLICY_RISK_FLOORS.get(operation, 1.0)
    serialized = canonical_json(step).lower()
    if SECRET_EXFILTRATION_PATTERN.search(serialized):
        return 1.0
    if any(term in serialized for term in ('"delete"', '"drop"', '"destroy"', '"overwrite"')):
        floor = max(floor, POLICY_RISK_FLOORS["destructive"])
    if any(term in serialized for term in ('"pay"', '"transfer"', '"purchase"', '"trade"')):
        floor = max(floor, POLICY_RISK_FLOORS["financial"])
    return floor


def _absolute_policy_blocks(
    route: RouteManifest,
    step: dict[str, Any],
    tool: dict[str, Any],
) -> list[str]:
    flags: list[str] = []
    serialized = canonical_json(step)
    if SECRET_EXFILTRATION_PATTERN.search(serialized):
        flags.append("secret_exfiltration")

    step_namespaces = [str(item) for item in step.get("namespaces", [])]
    if any(namespace not in route.namespaces for namespace in step_namespaces):
        flags.append("namespace_escape")
    try:
        validate_namespace_access(step_namespaces, route.project_id)
    except ValueError:
        flags.append("cross_client_retrieval")

    allowed_pillars = {str(item) for item in tool.get("allowed_pillars", [])}
    if allowed_pillars and route.primary_pillar not in allowed_pillars:
        flags.append("pillar_scope_violation")

    allowed_namespaces = {str(item) for item in tool.get("allowed_namespaces", [])}
    if allowed_namespaces and "*" not in allowed_namespaces:
        if any(namespace not in allowed_namespaces for namespace in step_namespaces):
            flags.append("namespace_escape")
    return flags


def _parse_tool_catalog(value: Any) -> dict[str, dict[str, Any]]:
    payload = model_payload(value)
    if payload in (None, "", {}):
        return {key: dict(item) for key, item in DEFAULT_TOOL_CATALOG.items()}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Tool catalog must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Tool catalog must be a JSON object keyed by tool ID")
    catalog = {key: dict(item) for key, item in DEFAULT_TOOL_CATALOG.items()}
    for key, item in payload.items():
        if not isinstance(item, dict):
            raise ValueError(f"Tool definition for {key!r} must be an object")
        catalog[str(key)] = sanitize_payload(item)
    return catalog


def _parse_permit(value: Any) -> tuple[ExecutionPermit | None, str | None]:
    payload = model_payload(value)
    if payload in (None, "", {}):
        return None, None
    try:
        return ExecutionPermit.model_validate(payload), None
    except Exception:
        return None, "invalid_permit_shape"


def _permit_allows(permit: ExecutionPermit | None, action_hash: str) -> bool:
    if permit is None:
        return False
    now = utc_now()
    expires_at = permit.expires_at.astimezone(timezone.utc)
    return (
        permit.action_hash == action_hash
        and permit.approved
        and permit.verified_by_gateway
        and not permit.consumed
        and expires_at > now
    )


def _risk(value: Any, *, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not 0 <= parsed <= 1:
        return default
    return parsed


def _flag_reason(flag: str) -> str:
    return {
        "unknown_tool": "Unknown tools are always blocked",
        "secret_exfiltration": "Secret exfiltration is always blocked",
        "namespace_escape": "The action escapes the routed namespace",
        "cross_client_retrieval": "Cross-client retrieval is forbidden",
        "permit_tampering": "Permit shape or action binding is invalid",
        "pillar_scope_violation": "The tool is not authorized for the active pillar",
    }.get(flag, flag)


class LifeOSExecutionGovernor(Component):
    display_name = "LifeOS Execution Governor"
    description = "Applies deterministic Protocol 001 governance without executing tools."
    icon = "ShieldCheck"
    name = "LifeOSExecutionGovernor"

    inputs = [
        DataInput(name="route_manifest", display_name="Route Manifest"),
        DataInput(name="execution_plan", display_name="Execution Plan"),
        MultilineInput(name="tool_catalog_json", display_name="Tool Catalog JSON", value="{}"),
        DataInput(name="approval_permit", display_name="Approval Permit"),
    ]

    outputs = [
        Output(name="approved_plan", display_name="Approved Plan", method="build_approved_plan"),
        Output(name="decision", display_name="Decision", method="build_decision"),
        Output(
            name="approval_request",
            display_name="Approval Request",
            method="build_approval_request",
        ),
        Output(name="audit_event", display_name="Audit Event", method="build_audit_event"),
    ]

    def _govern(self) -> dict[str, Any]:
        if not hasattr(self, "_governor_cache") or self._governor_cache is None:
            self._governor_cache = govern_execution(
                self.route_manifest,
                self.execution_plan,
                self.tool_catalog_json,
                self.approval_permit,
            )
        return self._governor_cache

    def build_approved_plan(self) -> Data:
        result = self._govern()
        self.status = result["decision"]["overall_decision"]
        return Data(data=result["approved_plan"])

    def build_decision(self) -> Data:
        return Data(data=self._govern()["decision"])

    def build_approval_request(self) -> Data:
        return Data(data=self._govern()["approval_request"])

    def build_audit_event(self) -> Data:
        return Data(data=self._govern()["audit_event"])
