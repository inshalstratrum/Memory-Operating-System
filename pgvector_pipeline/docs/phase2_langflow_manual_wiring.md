# Shali Brain v3 Phase 2: Manual Langflow Wiring

This guide targets Langflow `1.9.3`. It documents a manual canvas build and does
not authorize editing flow JSON, changing Docker volumes, installing packages,
or enabling Phase 3 tools.

## Component Files

Load these files together because the components import the shared contracts:

```text
lifeos_memory/langflow_components/lifeos_contracts.py
lifeos_memory/langflow_components/lifeos_sovereign_router.py
lifeos_memory/langflow_components/lifeos_temporal_fusion_retriever.py
lifeos_memory/langflow_components/lifeos_context_architect.py
lifeos_memory/langflow_components/lifeos_planner.py
lifeos_memory/langflow_components/lifeos_execution_governor.py
lifeos_memory/langflow_components/lifeos_executor_stub.py
lifeos_memory/langflow_components/lifeos_critics.py
lifeos_memory/langflow_components/lifeos_finalizer.py
```

Do not use the legacy `LifeOSSupabaseMemoryRetriever` or `LifeOSAuditLogger`
from `lifeos_supabase_memory.py` in this flow. They accept a Supabase service
credential and are outside the Shali Brain v3 security contract.

The source files are ready, but this phase does not copy them into the running
container or restart Langflow. If they are not already indexed through
`LANGFLOW_COMPONENTS_PATH`, deployment into `/app/data/lifeos_components`
requires separate approval because it mutates container state.

## Safe Defaults

```text
Temporal Retriever.result_count = 8
Temporal Retriever.include_sensitive = false
Temporal Retriever.memory_api_url = http://host.docker.internal:3000/api/memory
Context Architect.max_memories = 8
Context Architect.max_context_characters = 16000
Context Architect.cloud_context_allowed = true
Planner.effort_mode = balanced
Governor.tool_catalog_json = {}
Governor.approval_permit = unconnected
Finalizer.create_memory_candidate = true
```

`tool_catalog_json = {}` enables only the three built-in internal tools:

```text
internal.context_synthesis
internal.response_draft
internal.noop
```

No calendar, web, Python, financial, destructive, or client-facing tool exists
in Phase 2.

## Canvas Order

Place the nodes left to right:

```text
Chat Input
  -> LifeOS Sovereign Router
  -> LifeOS Temporal Fusion Retriever
  -> LifeOS Context Architect
  -> LifeOS Planner
  -> LifeOS Execution Governor
  -> LifeOS Executor Stub
  -> LifeOS Evidence Critic
  -> LifeOS Policy Critic
  -> LifeOS Finalizer
  -> Chat Output
```

The two critics run in parallel after the Executor Stub and both feed the
Finalizer.

## Exact Wires

### Input And Routing

```text
Chat Input.message
  -> LifeOSSovereignRouter.user_input

LifeOSSovereignRouter.clean_query
  -> LifeOSTemporalFusionRetriever.query

LifeOSSovereignRouter.route_manifest
  -> LifeOSTemporalFusionRetriever.route_manifest
```

Set the Router `namespace` manually. For client work, use exactly one client
namespace and its matching project ID:

```text
namespace = client_alpha
project_id = alpha
```

The router always includes `lifeos_core`. Related pillars are limited to two and
require both router confidence `>= 0.75` and explicit bridge reasons.

### Retrieval And Context

```text
LifeOSSovereignRouter.route_manifest
  -> LifeOSContextArchitect.route_manifest

LifeOSTemporalFusionRetriever.fused_memories
  -> LifeOSContextArchitect.retrieved_memories
```

Leave `recent_context` unconnected until a server-controlled conversation
history source exists. `pillar_rules_json = {}` uses the embedded four-pillar
rules.

Use `LifeOSContextArchitect.context_package` only for local orchestration.
Use `LifeOSContextArchitect.sanitized_cloud_context` as the only permissible
context source for any future OpenRouter model node.

### Planning And Governance

```text
LifeOSSovereignRouter.route_manifest
  -> LifeOSPlanner.route_manifest

LifeOSContextArchitect.context_package
  -> LifeOSPlanner.context_package

LifeOSSovereignRouter.route_manifest
  -> LifeOSExecutionGovernor.route_manifest

LifeOSPlanner.execution_plan
  -> LifeOSExecutionGovernor.execution_plan
```

Keep `approval_permit` unconnected in Phase 2. The governor never verifies PINs
or signatures. Risk is:

```text
max(step.estimated_risk, tool.risk_floor, deterministic_policy_floor)
```

Risk `<= 0.05` may be allowed. Risk `> 0.05` is held for explicit approval.
Unknown tools, secret exfiltration, namespace escape, cross-client retrieval,
and permit tampering are blocked.

### Executor Stub

```text
LifeOSExecutionGovernor.approved_plan
  -> LifeOSExecutorStub.approved_plan

LifeOSContextArchitect.context_package
  -> LifeOSExecutorStub.context_package
```

The stub creates structured no-op `ToolResult` objects. It performs no network,
filesystem, process, financial, destructive, or client-facing action.

### Evidence Critic

```text
LifeOSPlanner.execution_plan
  -> LifeOSEvidenceCritic.execution_plan

LifeOSExecutionGovernor.decision
  -> LifeOSEvidenceCritic.governor_decision

LifeOSExecutorStub.tool_results
  -> LifeOSEvidenceCritic.tool_results

LifeOSContextArchitect.context_package
  -> LifeOSEvidenceCritic.context_package

LifeOSExecutorStub.response_draft
  -> LifeOSEvidenceCritic.response_draft
```

### Policy Critic

```text
LifeOSSovereignRouter.route_manifest
  -> LifeOSPolicyCritic.route_manifest

LifeOSPlanner.execution_plan
  -> LifeOSPolicyCritic.execution_plan

LifeOSExecutionGovernor.decision
  -> LifeOSPolicyCritic.governor_decision

LifeOSExecutorStub.tool_results
  -> LifeOSPolicyCritic.tool_results

LifeOSContextArchitect.context_package
  -> LifeOSPolicyCritic.context_package

LifeOSContextArchitect.sanitized_cloud_context
  -> LifeOSPolicyCritic.sanitized_cloud_context
```

### Finalization

```text
Chat Input.message
  -> LifeOSFinalizer.original_query

LifeOSSovereignRouter.route_manifest
  -> LifeOSFinalizer.route_manifest

LifeOSContextArchitect.context_package
  -> LifeOSFinalizer.context_package

LifeOSPlanner.execution_plan
  -> LifeOSFinalizer.execution_plan

LifeOSExecutionGovernor.decision
  -> LifeOSFinalizer.governor_decision

LifeOSExecutorStub.tool_results
  -> LifeOSFinalizer.tool_results

LifeOSExecutorStub.response_draft
  -> LifeOSFinalizer.response_draft

LifeOSEvidenceCritic.verdict
  -> LifeOSFinalizer.evidence_verdict

LifeOSPolicyCritic.verdict
  -> LifeOSFinalizer.policy_verdict

LifeOSFinalizer.final_response
  -> Chat Output message input
```

`audit_ready_output` is a sanitized event payload only. Do not connect it to the
legacy audit logger. Database audit insertion belongs behind the future
credential-owning LifeOS Gateway.

`memory_candidates` contains draft-only candidates with
`canonical_write_allowed = false`. It is not a memory writer.

## OpenRouter Boundary

The Phase 2 components are deterministic and do not require a cloud model. If an
OpenRouter node is added later:

1. Feed it only `sanitized_cloud_context`.
2. Never feed raw retrieval output, local context, credentials, permits, or
   audit payloads.
3. Require `zdr=true`, `data_collection=deny`, and parameter enforcement.
4. Treat model plans and risk estimates as advisory; the deterministic Governor
   remains authoritative.
5. Never store raw chain-of-thought. Store only typed plans, verdicts, tool
   results, provenance, and final answers.

## Manual Verification Prompts

```text
DEEN: What should anchor my morning launch after Fajr?
NAFS_AQL: Build a sustainable sleep and study plan.
MAAL: Review my Upwork proposal workflow.
NASL_KHALQ: Draft a considerate reply to my team.
MIXED: How should zakat affect my business cash planning?
RISK: Send payment to the client now.
UNKNOWN TOOL: Browse the web and execute Python for this.
CLIENT ESCAPE: Use client_alpha context while project_id is beta.
```

Expected results:

```text
The four single-pillar prompts route to their matching pillar.
The mixed prompt may bridge only at confidence >= 0.75 with a reason.
The risky prompt enters requires_approval and is absent from approved_plan.
Unknown Phase 3 tools are blocked.
Client/project mismatch fails before retrieval.
The final response never claims that an external action occurred.
```

## Export And Backup

Do not hand-edit flow JSON.

### Flow Export

1. Save the flow in Langflow.
2. Use the Langflow UI flow menu and choose the JSON export/download action.
3. Store the exported file under a versioned LifeOS backup directory.
4. Import that export into a fresh test project before treating it as recoverable.

### `/app/data` Backup

The following is a manual future operation and was not run in Phase 2:

```powershell
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$target = "D:\LifeOS\backups\langflow\$stamp"
New-Item -ItemType Directory -Path $target
docker cp langflow:/app/data/. $target
Get-ChildItem -LiteralPath $target -Recurse
```

For a consistency-sensitive backup, first export the flow through the UI and
request explicit approval before stopping or restarting the container. Never
delete or replace `/app/data` as part of a backup.
