# Shali Brain v3: Sovereign Agentic Architecture

## Summary
- Replace the monolithic orchestrator with bounded Langflow subflows: **Route → Retrieve → Plan → Govern → Execute → Critic → Finalize**.
- Preserve chosen defaults: dual-zone inference, controlled cross-pillar bridges, tiered model spending, and conservative autonomy.
- Pin Langflow to `1.9.3`; export every stable flow to version control and back up `/app/data`.
- Remove the Supabase service-role key from Langflow after introducing the internal LifeOS Gateway.

## Agentic Architecture
- **Sovereign Router:** Runs locally and emits a typed `RouteManifest`: primary pillar, up to two related pillars, bridge reasons, namespaces, task class, sensitivity, complexity, tool needs, and confidence.
- **Pillar Specialists:** Four isolated Run Flow subflows. Deen uses approved cited sources only; Nafs/Aql cannot diagnose; Maal cannot perform financial/client actions; Nasl/Khalq produces communication drafts only.
- **Context Architect:** Retrieves memories, relational state, recent conversation, and pillar rules. It exposes only minimum-necessary sanitized context to cloud models.
- **Planner:** Produces typed steps, expected evidence, tool requirements, risk estimates, and completion criteria. Complex tasks generate two candidate plans for deterministic selection.
- **Execution Governor:** Applies Protocols 000–003 before every step. It is authoritative; LLM risk estimates are advisory.
- **Executor:** Receives only governor-approved steps. It may invoke bounded specialist subflows or tools but cannot invent tools or expand scope.
- **Critics:** An evidence critic checks factual/tool-result support; a deterministic policy critic checks pillar, consent, namespace, and Protocol 001 compliance.
- **Finalizer:** Synthesizes only accepted evidence, provides provenance, and creates draft memory candidates. It never stores raw chain-of-thought.
- Default budget: two repair cycles, eight tool calls, 12,000 total model tokens, 120-second wall time. Deep mode allows three repair cycles and 30,000 tokens.

```text
Input -> Local Router -> Hybrid Retrieval -> Context Architect -> Planner
      -> Execution Governor
      -> Approval wait OR Executor -> Evidence Critic + Policy Critic
      -> bounded repair -> Finalizer -> Audit -> Output
```

## Contracts And Control Plane
- Add typed contracts: `RouteManifest`, `ExecutionPlan`, `ActionRequest`, `ExecutionPermit`, `ToolResult`, `CriticVerdict`, and `MemoryCandidate`.
- Persist operational state in `life_agent_runs`, `life_agent_steps`, `life_approval_requests`, `life_memory_candidates`, and `life_conversation_messages`. Keep `life_audit_log` append-only.
- Build an internal, non-public `lifeos-gateway` service. It owns database/tool credentials and exposes narrowly scoped memory, audit, approval-verification, and MCP tool interfaces.
- Langflow receives no service-role key. The gateway uses a dedicated `lifeos_orchestrator` PostgreSQL role with only RPC execution and audit insertion privileges.
- Next.js approval UI verifies the authenticated local session plus an Argon2id Master PIN. It issues an Ed25519-signed, single-use permit bound to the SHA-256 hash of the exact action, expiring after 120 seconds.
- Risk is `max(model_estimate, tool_registry_floor, deterministic_policy_floor)`. Any value above `0.05` enters approval state; unknown tools, secret exfiltration, namespace escape, and permit tampering are always blocked.
- OpenRouter receives only sanitized context with `zdr=true`, `data_collection=deny`, and parameter enforcement. Sensitive/secret context and all routing, embeddings, policy, and database work remain local.
- Tiered inference: local model for routing/simple responses; `openrouter/auto` for ordinary sanitized work; premium planner/critic models are environment-configured and used only for complex tasks.

## Secure Tool Strategy
- Expose tools through a local MCP server registered with Langflow 1.9.3. Connect MCP tools only to the bounded Executor, never directly to the supervisor.
- Initial read-only tools:
  - `calendar.list_events`: read-only OAuth scope; tokens remain in the gateway.
  - `web.fetch_allowlisted`: blocks private IPs, redirects to private networks, oversized payloads, unsafe content types, and unauthorized domains.
  - `python.analyze`: isolated non-root worker, no network, read-only filesystem, temporary scratch storage, CPU/memory/PID limits, and hard timeout.
- Tool schemas declare allowed pillars, namespaces, operation class, deterministic risk floor, input/output schema, timeout, and evidence format.
- Later mutations reuse the same interface but require an action-bound permit. External, financial, destructive, and client-facing actions can never use unattended autopilot.
- Every request, approval, execution, result hash, failure, and retry is written to `life_audit_log`.

## Advanced RAG
- Add a generated weighted `tsvector` column and GIN index alongside the existing `vector(384)` HNSW index.
- Implement `lifeos_hybrid_search(query_text, query_embedding, primary_pillar, related_pillars, collections, sensitivity_ceiling, match_count)`.
- Generate 40 dense, 40 lexical, and 20 entity-relationship candidates. Fuse them with RRF using `k=60`.
- Query profiles adjust weights: conceptual favors dense retrieval; identifiers favor lexical/entity; relational queries favor entity edges; temporal queries favor recency.
- Locally rerank the top 20 with `cross-encoder/ms-marco-MiniLM-L-6-v2`, then apply MMR with `lambda=0.75` and return eight diverse results. The reranker emits scalar relevance and does not violate the 384-dimensional embedding contract.
- Final score: 45% reranker, 25% RRF, 10% source authority, 10% confidence, and 10% temporal relevance.
- Suggested decay half-lives: short-term 2 days, tasks 7 days, agent traces 30 days, episodic 45 days, semantic 365 days; canonical/persona memories do not automatically decay.
- Search primary pillar plus `lifeos_core`. Related pillars require router confidence ≥0.75 and an explicit bridge reason. Client namespaces always require an exact `project_id`; cross-client retrieval is forbidden.
- After accepted responses, a Memory Curator creates deduplicated draft candidates with provenance and sensitivity classification. Promotion to canonical memory is separate from chat execution.

## New Custom Component
Create `LifeOSExecutionGovernor`, replacing the current manually supplied risk scalar with deterministic plan-level governance:

```python
class LifeOSExecutionGovernor(Component):
    inputs = [route_manifest, execution_plan, tool_catalog, approval_permit]
    outputs = [approved_plan, decision, approval_request, audit_event]

    def govern(self):
        route = RouteManifest.model_validate(self.route_manifest.data)
        plan = ExecutionPlan.model_validate(self.execution_plan.data)

        for step in plan.steps:
            tool = catalog.require(step.tool_id)
            assert_scope(step, route, tool)
            risk = max(step.estimated_risk, tool.risk_floor, policy_floor(step))
            action_hash = sha256(canonical_json(step))

            if is_absolute_block(step, route):
                decision.block(step, risk, action_hash)
            elif risk > 0.05 or requires_explicit_approval(step):
                decision.require_permit(step, risk, action_hash)
            else:
                decision.allow(step, risk, action_hash)

        gateway.append_audit(decision.audit_payload())
        return typed_outputs(decision)
```

The component never executes tools, verifies PINs, or stores secrets. Permit verification and atomic one-time consumption occur inside `lifeos-gateway`.

## Test Plan
- Golden routing tests for all pillars, mixed-pillar prompts, client isolation, and bridge confidence.
- Retrieval evaluation using Recall@8, MRR, nDCG@8, provenance accuracy, temporal queries, exact names, and adversarial context bleed.
- Confirm every generated/query vector has 384 dimensions and filtered HNSW searches return sufficient results using iterative scans.
- Verify sensitive context never enters OpenRouter requests and cloud failure falls back locally with a visible degraded-state flag.
- Test permit expiry, replay, action-hash modification, wrong PIN, unknown tools, SSRF, path traversal, Python timeout, and sandbox escape attempts.
- Confirm risk `>0.05` cannot reach execution without a matching one-time permit.
- Confirm critics reject unsupported claims, incomplete steps, fabricated tool results, and policy violations.
- Pin and export flow JSON, restore it into a fresh Langflow container, and prove `/app/data` persistence.

## Assumptions
- Supabase remains the canonical relational/vector store; Langflow chat storage is not canonical memory.
- Existing memory and audit tables are preserved through additive migrations.
- The current Next.js interface becomes the sole approval control plane.
- Relevant implementation references: [Langflow Run Flow](https://docs.langflow.org/run-flow), [Langflow Agents](https://docs.langflow.org/agents), [Langflow MCP Tools](https://docs.langflow.org/mcp-tools), [Supabase Hybrid Search](https://supabase.com/docs/guides/ai/hybrid-search), [pgvector](https://github.com/pgvector/pgvector), and [OpenRouter Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection).
