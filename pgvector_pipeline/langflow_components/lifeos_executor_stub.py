from __future__ import annotations

"""Non-mutating Phase 2 executor stub.

It returns structured ToolResult records for internal planning tests only. It
does not call MCP, execute Python, access the network, or create external effects.
"""

from typing import Any

from langflow.custom import Component
from langflow.io import DataInput, Output
from langflow.schema import Data

try:
    from lifeos_contracts import (
        ToolResult,
        model_payload,
        sanitize_payload,
        sanitize_text,
        sha256_hex,
    )
except ImportError:
    from .lifeos_contracts import (
        ToolResult,
        model_payload,
        sanitize_payload,
        sanitize_text,
        sha256_hex,
    )

STUB_TOOLS = {
    "internal.context_synthesis",
    "internal.response_draft",
    "internal.noop",
}


def execute_stub(approved_plan_value: Any, context_value: Any) -> dict[str, Any]:
    approved_plan = model_payload(approved_plan_value) or {}
    context = sanitize_payload(model_payload(context_value) or {})
    if not isinstance(approved_plan, dict):
        raise ValueError("Approved plan must be an object")

    plan_id = str(approved_plan.get("plan_id") or "")
    route = approved_plan.get("route") if isinstance(approved_plan.get("route"), dict) else {}
    pillar = str(route.get("primary_pillar") or "nafs_aql")
    steps = approved_plan.get("steps") if isinstance(approved_plan.get("steps"), list) else []
    provenance = context.get("provenance", []) if isinstance(context, dict) else []
    available_evidence = {
        str(item.get("memory_id"))
        for item in provenance
        if isinstance(item, dict) and item.get("memory_id")
    }

    results: list[dict[str, Any]] = []
    response_draft = {
        "contract": "shali.response_draft.v3",
        "text": "",
        "claims": [],
        "evidence_ids": [],
        "external_action_claimed": False,
    }
    for step in steps:
        if not isinstance(step, dict):
            continue
        tool_id = str(step.get("tool_id") or "")
        step_id = str(step.get("step_id") or "")
        namespaces = [str(item) for item in step.get("namespaces", [])]
        requested_evidence = [str(item) for item in step.get("expected_evidence", [])]
        evidence_ids = [item for item in requested_evidence if item in available_evidence]

        if tool_id not in STUB_TOOLS:
            output = {"message": "Executor stub refused a non-internal tool"}
            status = "blocked"
            error_code = "phase3_tool_execution_disabled"
        elif tool_id == "internal.context_synthesis":
            output = {
                "message": "Accepted context references prepared for bounded synthesis",
                "provenance_count": len(evidence_ids),
                "context_hash": sha256_hex(context),
            }
            status = "no_op"
            error_code = None
        elif tool_id == "internal.response_draft":
            query = sanitize_text(route.get("query") or context.get("route", {}).get("query") or "")
            response_draft = {
                "contract": "shali.response_draft.v3",
                "text": (
                    f"I prepared a bounded draft for: {query}"
                    if query
                    else "I prepared a bounded response draft from the accepted context."
                ),
                "claims": [],
                "evidence_ids": evidence_ids,
                "external_action_claimed": False,
                "execution_notice": "No real-world action was executed in Phase 2.",
            }
            output = {
                "message": "Draft response prepared without external execution",
                "draft_hash": sha256_hex(response_draft),
            }
            status = "no_op"
            error_code = None
        else:
            output = {"message": "Internal no-op completed"}
            status = "no_op"
            error_code = None

        result_seed = {
            "plan_id": plan_id,
            "step_id": step_id,
            "tool_id": tool_id,
            "status": status,
            "output": output,
            "evidence_ids": evidence_ids,
        }
        result = ToolResult(
            plan_id=plan_id,
            step_id=step_id,
            tool_id=tool_id,
            status=status,
            output=output,
            evidence_ids=evidence_ids,
            namespaces=namespaces,
            pillar=pillar,
            mutation_performed=False,
            external_effect=False,
            result_hash=sha256_hex(result_seed),
            error_code=error_code,
        )
        results.append(result.model_dump(mode="json"))

    return {
        "tool_results": {
            "contract": "shali.tool_results.v3",
            "phase3_tools_enabled": False,
            "results": results,
        },
        "response_draft": response_draft,
    }


class LifeOSExecutorStub(Component):
    display_name = "LifeOS Executor Stub"
    description = "Returns non-mutating internal ToolResult records; no real tools are executed."
    icon = "CirclePause"
    name = "LifeOSExecutorStub"

    inputs = [
        DataInput(name="approved_plan", display_name="Approved Plan"),
        DataInput(name="context_package", display_name="Context Package"),
    ]

    outputs = [
        Output(name="tool_results", display_name="Tool Results", method="build_tool_results"),
        Output(name="response_draft", display_name="Response Draft", method="build_response_draft"),
    ]

    def _execute(self) -> dict[str, Any]:
        if not hasattr(self, "_stub_cache") or self._stub_cache is None:
            self._stub_cache = execute_stub(self.approved_plan, self.context_package)
        return self._stub_cache

    def build_tool_results(self) -> Data:
        result = self._execute()["tool_results"]
        self.status = f"{len(result['results'])} no-op result(s)"
        return Data(data=result)

    def build_response_draft(self) -> Data:
        return Data(data=self._execute()["response_draft"])
