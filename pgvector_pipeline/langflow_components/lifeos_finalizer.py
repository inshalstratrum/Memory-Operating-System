from __future__ import annotations

"""Evidence-only final response and audit-ready output for Shali Brain v3."""

from typing import Any

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, MessageInput, Output
from langflow.schema import Data
from langflow.schema.message import Message

try:
    from lifeos_contracts import (
        CriticVerdict,
        MemoryCandidate,
        RouteManifest,
        model_payload,
        sanitize_payload,
        sanitize_text,
        sha256_hex,
        utc_now,
    )
except ImportError:
    from .lifeos_contracts import (
        CriticVerdict,
        MemoryCandidate,
        RouteManifest,
        model_payload,
        sanitize_payload,
        sanitize_text,
        sha256_hex,
        utc_now,
    )


def finalize_response(
    original_query_value: Any,
    route_value: Any,
    context_value: Any,
    execution_plan_value: Any,
    governor_decision_value: Any,
    tool_results_value: Any,
    response_draft_value: Any,
    evidence_verdict_value: Any,
    policy_verdict_value: Any,
    *,
    create_memory_candidate: bool = True,
) -> dict[str, Any]:
    route = RouteManifest.model_validate(model_payload(route_value))
    context = sanitize_payload(model_payload(context_value) or {})
    plan = sanitize_payload(model_payload(execution_plan_value) or {})
    decision = sanitize_payload(model_payload(governor_decision_value) or {})
    tool_results = sanitize_payload(model_payload(tool_results_value) or {})
    response_draft = sanitize_payload(model_payload(response_draft_value) or {})
    evidence_verdict = CriticVerdict.model_validate(model_payload(evidence_verdict_value))
    policy_verdict = CriticVerdict.model_validate(model_payload(policy_verdict_value))
    original_query = sanitize_text(getattr(original_query_value, "text", original_query_value))

    critics_accept = (
        evidence_verdict.verdict == "accept"
        and policy_verdict.verdict == "accept"
    )
    approval_pending = decision.get("overall_decision") == "requires_approval"
    blocked = decision.get("overall_decision") == "block"

    if not critics_accept:
        final_text = (
            "I stopped this response because the evidence or policy review failed. "
            "No external action was taken."
        )
    elif blocked:
        final_text = (
            "The execution governor blocked one or more plan steps. "
            "No external action was taken."
        )
    else:
        draft_text = sanitize_text(response_draft.get("text", ""))
        final_text = draft_text or "The approved internal analysis completed without external execution."
        if approval_pending:
            final_text = (
                f"{final_text}\n\nExplicit approval is required before any held action can proceed. "
                "No held action was executed."
            )

    provenance = _accepted_provenance(context, evidence_verdict)
    if provenance and critics_accept:
        labels = [
            str(item.get("source_title") or item.get("source_uri") or item.get("memory_id"))
            for item in provenance[:8]
        ]
        final_text = f"{final_text}\n\nProvenance: {', '.join(labels)}"
    final_text = sanitize_text(final_text)

    memory_candidates: list[dict[str, Any]] = []
    if create_memory_candidate and critics_accept and not blocked:
        namespace = next(
            (item for item in route.namespaces if item != "lifeos_core"),
            "lifeos_core",
        )
        candidate_seed = {
            "query": original_query,
            "response": final_text,
            "route": route.model_dump(mode="json"),
            "provenance": provenance,
        }
        candidate = MemoryCandidate(
            candidate_id=f"candidate_{sha256_hex(candidate_seed)[:24]}",
            content=final_text,
            pillar=route.primary_pillar,
            namespace=namespace,
            memory_kind="episodic",
            sensitivity=route.sensitivity,
            confidence=min(route.confidence, 0.85),
            provenance=provenance,
            consent_level="draft",
            canonical_write_allowed=False,
        )
        memory_candidates.append(candidate.model_dump(mode="json"))

    audit_ready = sanitize_payload(
        {
            "contract": "shali.audit_ready_output.v3",
            "event_type": "orchestration.finalized",
            "occurred_at": utc_now().isoformat(),
            "actor": "langflow",
            "source": "lifeos_finalizer",
            "route": {
                "primary_pillar": route.primary_pillar,
                "related_pillars": route.related_pillars,
                "namespaces": route.namespaces,
                "project_id": route.project_id,
                "sensitivity": route.sensitivity,
            },
            "plan_id": plan.get("plan_id"),
            "governor_decision": decision.get("overall_decision"),
            "evidence_verdict": evidence_verdict.model_dump(mode="json"),
            "policy_verdict": policy_verdict.model_dump(mode="json"),
            "tool_result_hash": sha256_hex(tool_results),
            "final_response_hash": sha256_hex(final_text),
            "memory_candidate_ids": [item["candidate_id"] for item in memory_candidates],
            "external_action_executed": False,
            "canonical_memory_written": False,
            "reasoning_trace_persisted": False,
        }
    )
    audit_ready["payload_hash"] = sha256_hex(audit_ready)
    return {
        "final_text": final_text,
        "audit_ready_output": audit_ready,
        "memory_candidates": {
            "contract": "shali.memory_candidates.v3",
            "status": "draft_only",
            "canonical_write_allowed": False,
            "candidates": memory_candidates,
        },
    }


def _accepted_provenance(
    context: dict[str, Any],
    evidence_verdict: CriticVerdict,
) -> list[dict[str, Any]]:
    accepted_ids = set(evidence_verdict.evidence_ids)
    provenance: list[dict[str, Any]] = []
    for item in context.get("provenance", []):
        if not isinstance(item, dict):
            continue
        memory_id = str(item.get("memory_id") or "")
        if memory_id and memory_id in accepted_ids:
            provenance.append(sanitize_payload(item))
    return provenance


class LifeOSFinalizer(Component):
    display_name = "LifeOS Finalizer"
    description = "Produces an evidence-only response, provenance, draft memories, and audit payload."
    icon = "BadgeCheck"
    name = "LifeOSFinalizer"

    inputs = [
        MessageInput(name="original_query", display_name="Original Query"),
        DataInput(name="route_manifest", display_name="Route Manifest"),
        DataInput(name="context_package", display_name="Context Package"),
        DataInput(name="execution_plan", display_name="Execution Plan"),
        DataInput(name="governor_decision", display_name="Governor Decision"),
        DataInput(name="tool_results", display_name="Tool Results"),
        DataInput(name="response_draft", display_name="Response Draft"),
        DataInput(name="evidence_verdict", display_name="Evidence Verdict"),
        DataInput(name="policy_verdict", display_name="Policy Verdict"),
        BoolInput(
            name="create_memory_candidate",
            display_name="Create Draft Memory Candidate",
            value=True,
        ),
    ]

    outputs = [
        Output(name="final_response", display_name="Final Response", method="build_final_response"),
        Output(
            name="audit_ready_output",
            display_name="Audit-ready Output",
            method="build_audit_output",
        ),
        Output(
            name="memory_candidates",
            display_name="Draft Memory Candidates",
            method="build_memory_candidates",
        ),
    ]

    def _finalize(self) -> dict[str, Any]:
        if not hasattr(self, "_finalizer_cache") or self._finalizer_cache is None:
            self._finalizer_cache = finalize_response(
                self.original_query,
                self.route_manifest,
                self.context_package,
                self.execution_plan,
                self.governor_decision,
                self.tool_results,
                self.response_draft,
                self.evidence_verdict,
                self.policy_verdict,
                create_memory_candidate=bool(self.create_memory_candidate),
            )
        return self._finalizer_cache

    def build_final_response(self) -> Message:
        result = self._finalize()
        self.status = "finalized"
        return Message(text=result["final_text"])

    def build_audit_output(self) -> Data:
        return Data(data=self._finalize()["audit_ready_output"])

    def build_memory_candidates(self) -> Data:
        return Data(data=self._finalize()["memory_candidates"])
