from __future__ import annotations

"""Evidence and deterministic policy critics for Shali Brain v3 Phase 2."""

import re
from typing import Any

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema import Data

try:
    from lifeos_contracts import (
        CriticVerdict,
        ExecutionPlan,
        RouteManifest,
        ToolResult,
        model_payload,
    )
except ImportError:
    from .lifeos_contracts import (
        CriticVerdict,
        ExecutionPlan,
        RouteManifest,
        ToolResult,
        model_payload,
    )

EXECUTION_CLAIM_PATTERN = re.compile(
    r"(?i)\b(?:i|we|shali)\s+(?:sent|published|paid|transferred|deleted|booked|executed|contacted)\b"
)
SENSITIVE_LEVELS = {"sensitive", "secret"}


def evaluate_evidence(
    plan_value: Any,
    governor_decision_value: Any,
    tool_results_value: Any,
    context_value: Any,
    response_draft_value: Any,
) -> CriticVerdict:
    plan = ExecutionPlan.model_validate(model_payload(plan_value))
    decision = model_payload(governor_decision_value) or {}
    tool_payload = model_payload(tool_results_value) or {}
    context = model_payload(context_value) or {}
    draft = model_payload(response_draft_value) or {}

    plan_steps = {step.step_id: step for step in plan.steps}
    approved_ids = set(decision.get("approved_step_ids", []))
    available_evidence = {
        str(item.get("memory_id"))
        for item in context.get("provenance", [])
        if isinstance(item, dict) and item.get("memory_id")
    }

    findings: list[str] = []
    rejected_steps: set[str] = set()
    accepted_steps: set[str] = set()
    results = tool_payload.get("results", []) if isinstance(tool_payload, dict) else []
    for raw_result in results:
        try:
            result = ToolResult.model_validate(raw_result)
        except Exception:
            findings.append("Malformed or fabricated ToolResult object")
            continue
        step = plan_steps.get(result.step_id)
        if step is None:
            findings.append(f"ToolResult references unknown step {result.step_id}")
            rejected_steps.add(result.step_id)
            continue
        if result.step_id not in approved_ids:
            findings.append(f"ToolResult exists for non-approved step {result.step_id}")
            rejected_steps.add(result.step_id)
        if result.tool_id != step.tool_id:
            findings.append(f"ToolResult tool mismatch for step {result.step_id}")
            rejected_steps.add(result.step_id)
        if any(evidence_id not in available_evidence for evidence_id in result.evidence_ids):
            findings.append(f"ToolResult cites unavailable evidence for step {result.step_id}")
            rejected_steps.add(result.step_id)
        if result.mutation_performed or result.external_effect:
            findings.append(f"Phase 2 stub claims a forbidden real-world effect at {result.step_id}")
            rejected_steps.add(result.step_id)
        if result.step_id not in rejected_steps:
            accepted_steps.add(result.step_id)

    claims = draft.get("claims", []) if isinstance(draft, dict) else []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            findings.append(f"Claim {index} has an invalid shape")
            continue
        evidence_ids = [str(item) for item in claim.get("evidence_ids", [])]
        if not evidence_ids:
            findings.append(f"Claim {index} has no supporting evidence")
        elif any(evidence_id not in available_evidence for evidence_id in evidence_ids):
            findings.append(f"Claim {index} cites unavailable evidence")

    draft_text = str(draft.get("text", "")) if isinstance(draft, dict) else ""
    if EXECUTION_CLAIM_PATTERN.search(draft_text) or bool(draft.get("external_action_claimed")):
        findings.append("Response draft fabricates or claims a real-world action")

    expected_approved_results = {
        step_id
        for step_id in approved_ids
        if step_id in plan_steps
    }
    result_step_ids = {
        str(item.get("step_id"))
        for item in results
        if isinstance(item, dict) and item.get("step_id")
    }
    missing_results = expected_approved_results - result_step_ids
    for step_id in sorted(missing_results):
        findings.append(f"Approved step {step_id} has no ToolResult")
        rejected_steps.add(step_id)

    verdict = "reject" if findings else "accept"
    return CriticVerdict(
        critic="evidence",
        verdict=verdict,
        accepted_step_ids=sorted(accepted_steps - rejected_steps),
        rejected_step_ids=sorted(rejected_steps),
        findings=findings,
        repair_instructions=(
            ["Remove unsupported claims and provide ToolResults tied to accepted provenance"]
            if findings
            else []
        ),
        evidence_ids=sorted(available_evidence),
        policy_flags=[],
    )


def evaluate_policy(
    route_value: Any,
    plan_value: Any,
    governor_decision_value: Any,
    tool_results_value: Any,
    context_value: Any,
    cloud_context_value: Any,
) -> CriticVerdict:
    route = RouteManifest.model_validate(model_payload(route_value))
    plan = ExecutionPlan.model_validate(model_payload(plan_value))
    decision = model_payload(governor_decision_value) or {}
    tool_payload = model_payload(tool_results_value) or {}
    context = model_payload(context_value) or {}
    cloud_context = model_payload(cloud_context_value) or {}

    findings: list[str] = []
    flags: set[str] = set()
    rejected_steps: set[str] = set()
    approved_ids = set(decision.get("approved_step_ids", []))
    allowed_pillars = {route.primary_pillar, *route.related_pillars}
    allowed_namespaces = set(route.namespaces)

    if plan.route != route:
        findings.append("Plan route differs from the authoritative RouteManifest")
        flags.add("route_manifest_mismatch")

    for step_decision in decision.get("step_decisions", []):
        if not isinstance(step_decision, dict):
            findings.append("Malformed governor step decision")
            continue
        step_id = str(step_decision.get("step_id", ""))
        risk = _float(step_decision.get("effective_risk"), 1.0)
        allowed = step_decision.get("decision") == "allow"
        policy_flags = set(step_decision.get("policy_flags", []))
        if allowed and risk > 0.05 and "explicit_approval_verified" not in policy_flags:
            findings.append(f"Protocol 001 violation: {step_id} allowed above risk 0.05")
            flags.add("protocol_001")
            rejected_steps.add(step_id)
        if any(
            flag in policy_flags
            for flag in (
                "unknown_tool",
                "secret_exfiltration",
                "namespace_escape",
                "cross_client_retrieval",
                "permit_tampering",
            )
        ) and allowed:
            findings.append(f"Absolute policy block was bypassed at {step_id}")
            flags.update(policy_flags)
            rejected_steps.add(step_id)

    results = tool_payload.get("results", []) if isinstance(tool_payload, dict) else []
    accepted_steps: set[str] = set()
    for raw_result in results:
        try:
            result = ToolResult.model_validate(raw_result)
        except Exception:
            findings.append("Malformed ToolResult in policy review")
            flags.add("invalid_tool_result")
            continue
        if result.step_id not in approved_ids:
            findings.append(f"Executor produced a result for non-approved step {result.step_id}")
            flags.add("governor_bypass")
            rejected_steps.add(result.step_id)
        if result.pillar not in allowed_pillars:
            findings.append(f"ToolResult pillar escape at {result.step_id}")
            flags.add("pillar_scope_violation")
            rejected_steps.add(result.step_id)
        if any(namespace not in allowed_namespaces for namespace in result.namespaces):
            findings.append(f"ToolResult namespace escape at {result.step_id}")
            flags.add("namespace_escape")
            rejected_steps.add(result.step_id)
        if result.mutation_performed or result.external_effect:
            findings.append(f"Phase 2 executor performed a forbidden effect at {result.step_id}")
            flags.add("phase3_action_attempt")
            rejected_steps.add(result.step_id)
        if result.step_id not in rejected_steps:
            accepted_steps.add(result.step_id)

    for memory in context.get("memories", []) if isinstance(context, dict) else []:
        if not isinstance(memory, dict):
            continue
        pillar = str(memory.get("pillar", route.primary_pillar))
        namespace = str(memory.get("collection_name") or memory.get("namespace") or "lifeos_core")
        if pillar not in allowed_pillars:
            findings.append("Context contains a memory from an unauthorized pillar")
            flags.add("pillar_scope_violation")
        if namespace not in allowed_namespaces:
            findings.append("Context contains a memory from an unauthorized namespace")
            flags.add("namespace_escape")

    for memory in cloud_context.get("memories", []) if isinstance(cloud_context, dict) else []:
        if isinstance(memory, dict) and str(memory.get("sensitivity", "")).lower() in SENSITIVE_LEVELS:
            findings.append("Sensitive memory entered the cloud context")
            flags.add("sensitive_cloud_context")

    verdict = "reject" if findings else "accept"
    return CriticVerdict(
        critic="policy",
        verdict=verdict,
        accepted_step_ids=sorted(accepted_steps - rejected_steps),
        rejected_step_ids=sorted(rejected_steps),
        findings=findings,
        repair_instructions=(
            ["Return to the planner or governor; do not bypass deterministic policy"]
            if findings
            else []
        ),
        evidence_ids=[],
        policy_flags=sorted(flags),
    )


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class LifeOSEvidenceCritic(Component):
    display_name = "LifeOS Evidence Critic"
    description = "Rejects unsupported claims, fabricated effects, and invalid ToolResults."
    icon = "SearchCheck"
    name = "LifeOSEvidenceCritic"

    inputs = [
        DataInput(name="execution_plan", display_name="Execution Plan"),
        DataInput(name="governor_decision", display_name="Governor Decision"),
        DataInput(name="tool_results", display_name="Tool Results"),
        DataInput(name="context_package", display_name="Context Package"),
        DataInput(name="response_draft", display_name="Response Draft"),
    ]
    outputs = [
        Output(name="verdict", display_name="Evidence Verdict", method="build_verdict"),
    ]

    def build_verdict(self) -> Data:
        verdict = evaluate_evidence(
            self.execution_plan,
            self.governor_decision,
            self.tool_results,
            self.context_package,
            self.response_draft,
        )
        self.status = verdict.verdict
        return Data(data=verdict.model_dump(mode="json"))


class LifeOSPolicyCritic(Component):
    display_name = "LifeOS Policy Critic"
    description = "Checks pillar, namespace, sensitivity, and Protocol 001 compliance."
    icon = "ShieldAlert"
    name = "LifeOSPolicyCritic"

    inputs = [
        DataInput(name="route_manifest", display_name="Route Manifest"),
        DataInput(name="execution_plan", display_name="Execution Plan"),
        DataInput(name="governor_decision", display_name="Governor Decision"),
        DataInput(name="tool_results", display_name="Tool Results"),
        DataInput(name="context_package", display_name="Context Package"),
        DataInput(name="sanitized_cloud_context", display_name="Sanitized Cloud Context"),
    ]
    outputs = [
        Output(name="verdict", display_name="Policy Verdict", method="build_verdict"),
    ]

    def build_verdict(self) -> Data:
        verdict = evaluate_policy(
            self.route_manifest,
            self.execution_plan,
            self.governor_decision,
            self.tool_results,
            self.context_package,
            self.sanitized_cloud_context,
        )
        self.status = verdict.verdict
        return Data(data=verdict.model_dump(mode="json"))
