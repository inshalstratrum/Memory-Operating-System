from __future__ import annotations

"""Bounded deterministic planner for Shali Brain v3 Phase 2."""

from typing import Any

from langflow.custom import Component
from langflow.io import DataInput, DropdownInput, Output
from langflow.schema import Data

try:
    from lifeos_contracts import (
        ExecutionPlan,
        PlanStep,
        RouteManifest,
        model_payload,
        sanitize_payload,
        sha256_hex,
    )
except ImportError:
    from .lifeos_contracts import (
        ExecutionPlan,
        PlanStep,
        RouteManifest,
        model_payload,
        sanitize_payload,
        sha256_hex,
    )

INTERNAL_SYNTHESIS_TOOL = "internal.context_synthesis"
INTERNAL_DRAFT_TOOL = "internal.response_draft"


def build_execution_plan(
    route_value: Any,
    context_value: Any,
    *,
    effort_mode: str = "balanced",
) -> ExecutionPlan:
    route = RouteManifest.model_validate(model_payload(route_value))
    context = sanitize_payload(model_payload(context_value) or {})
    provenance = context.get("provenance", []) if isinstance(context, dict) else []
    evidence_ids = [
        str(item.get("memory_id"))
        for item in provenance
        if isinstance(item, dict) and item.get("memory_id")
    ]

    steps: list[PlanStep] = [
        PlanStep(
            step_id="step_01_context",
            title="Assemble accepted context",
            instruction=(
                "Use only the supplied context package and provenance. Do not infer tool results "
                "or expose hidden reasoning."
            ),
            tool_id=INTERNAL_SYNTHESIS_TOOL,
            operation_class="internal",
            namespaces=route.namespaces,
            expected_evidence=evidence_ids,
            estimated_risk=0.0,
            completion_criteria=[
                "Context remains inside routed pillars and namespaces",
                "Every retained factual memory has provenance",
            ],
            payload={
                "primary_pillar": route.primary_pillar,
                "related_pillars": route.related_pillars,
            },
        )
    ]

    for index, tool_need in enumerate(route.tool_needs, start=2):
        operation_class = _operation_class(tool_need)
        steps.append(
            PlanStep(
                step_id=f"step_{index:02d}_request",
                title=f"Request bounded capability: {tool_need}",
                instruction=(
                    "Request this capability from the governor. Phase 2 has no real tool "
                    "implementation, so execution must remain blocked or approval-gated."
                ),
                tool_id=tool_need,
                operation_class=operation_class,
                namespaces=route.namespaces,
                expected_evidence=[],
                estimated_risk=_advisory_risk(operation_class),
                completion_criteria=[
                    "Governor returns an explicit allow, approval, or block decision",
                    "No external effect occurs inside Phase 2",
                ],
                payload={"requested_by_router": True},
            )
        )

    response_step_index = len(steps) + 1
    steps.append(
        PlanStep(
            step_id=f"step_{response_step_index:02d}_draft",
            title="Draft bounded response",
            instruction=(
                "Produce a concise response using accepted evidence only. Mark uncertainty, "
                "preserve the pillar rules, and make no claim that a real-world action occurred."
            ),
            tool_id=INTERNAL_DRAFT_TOOL,
            operation_class="draft",
            namespaces=route.namespaces,
            expected_evidence=evidence_ids,
            estimated_risk=0.0,
            completion_criteria=[
                "Response uses accepted evidence only",
                "No raw chain-of-thought is included",
                "No external, financial, destructive, or client-facing action is represented as executed",
            ],
            payload={"task_class": route.task_class},
        )
    )

    deep = effort_mode == "deep" or route.complexity == "deep"
    plan_seed = {
        "route": route.model_dump(mode="json"),
        "steps": [step.model_dump(mode="json") for step in steps],
        "effort_mode": effort_mode,
    }
    return ExecutionPlan(
        plan_id=f"plan_{sha256_hex(plan_seed)[:20]}",
        route=route,
        objective=route.query,
        steps=steps,
        tool_requirements=list(route.tool_needs),
        max_repair_cycles=3 if deep else 2,
        max_tool_calls=8,
        max_model_tokens=30000 if deep else 12000,
        max_wall_time_seconds=120,
        completion_criteria=[
            "All steps receive deterministic governance",
            "Evidence and policy critics accept the result",
            "Final output contains provenance and no hidden reasoning",
        ],
        candidate_plan_count=2 if route.complexity in {"complex", "deep"} else 1,
    )


def _operation_class(tool_need: str) -> str:
    lowered = tool_need.lower()
    if lowered.startswith("calendar.") or lowered.startswith("web."):
        return "external_read"
    if lowered.startswith("python."):
        return "local_compute"
    if lowered.startswith("financial.") or "payment" in lowered:
        return "financial"
    if lowered == "external.action":
        return "external"
    return "unknown"


def _advisory_risk(operation_class: str) -> float:
    return {
        "internal": 0.0,
        "draft": 0.0,
        "external_read": 0.06,
        "local_compute": 0.04,
        "external": 0.15,
        "financial": 0.25,
        "destructive": 0.5,
        "client_facing": 0.15,
        "unknown": 1.0,
    }.get(operation_class, 1.0)


class LifeOSPlanner(Component):
    display_name = "LifeOS Planner"
    description = "Produces a bounded typed ExecutionPlan without executing tools."
    icon = "ListChecks"
    name = "LifeOSPlanner"

    inputs = [
        DataInput(name="route_manifest", display_name="Route Manifest"),
        DataInput(name="context_package", display_name="Context Package"),
        DropdownInput(
            name="effort_mode",
            display_name="Effort Mode",
            options=["balanced", "deep"],
            value="balanced",
        ),
    ]

    outputs = [
        Output(name="execution_plan", display_name="Execution Plan", method="build_plan"),
    ]

    def build_plan(self) -> Data:
        plan = build_execution_plan(
            self.route_manifest,
            self.context_package,
            effort_mode=str(self.effort_mode or "balanced"),
        )
        self.status = f"{len(plan.steps)} steps; {plan.max_model_tokens} token budget"
        return Data(data=plan.model_dump(mode="json"))
