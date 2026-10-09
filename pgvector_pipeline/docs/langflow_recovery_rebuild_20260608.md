# Langflow Recovery And Rebuild Checklist - 2026-06-08

## Recovery Findings

- `langflow.db` was not found under `D:\LifeOS` or `D:\Shali-ai-brain`.
- Recent JSON scan found one old flow-like artifact:
  - `D:\LifeOS\_LEGACY_QUARANTINE\MemoryOS_v5\LifeOS_Canonical_Architecture\Clients_Workspace_Flow.json.json`
- Per operator instruction, the old JSON artifact is not being recovered or imported.
- Langflow persistence is now fixed in:
  - `D:\LifeOS\_LEGACY_QUARANTINE\MemoryOS_v5\docker-compose.yml`
- Required compose state:
  - `user: root`
  - `./langflow_data:/app/data`
  - `../../lifeos_memory/langflow_components:/app/data/lifeos_components:ro`
  - `LANGFLOW_COMPONENTS_PATH=/app/data/lifeos_components`
  - `SUPABASE_URL=http://kong:8000`
  - `LIFEOS_DLP_MODE=true`

## Verified Runtime State

- Langflow container recreated with `docker compose down` and `docker compose up -d`.
- Langflow is reachable at `http://localhost:7860`.
- Host path `D:\LifeOS\_LEGACY_QUARANTINE\MemoryOS_v5\langflow_data` is mounted to `/app/data`.
- `/app/data` is writable inside the container.
- `lifeos_supabase_memory.py` is present at `/app/data/lifeos_components/lifeos_supabase_memory.py`.
- Custom component classes available:
  - `LifeOSSupabaseMemoryRetriever`
  - `LifeOSProtocolGate`
  - `LifeOSAuditLogger`

## Screenshot-Rebuild Node Inventory

Recreate the canvas visually from left to right:

1. `Read File`
2. `Split Text`
3. `Local Hugging Face Embeddings`
4. `Chat Input`
5. `Sovereign Intent Router`
6. `OpenRouter`
7. `LifeOSSupabaseMemoryRetriever`
8. `LifeOSProtocolGate`
9. `Context Funnel (Compressor)`
10. `Agentic Orchestrator`
11. `LifeOSAuditLogger`
12. `Chat Output`

The old screenshot contains a generic `Supabase` vector-store node. Replace that role with the Phase 2 custom `LifeOSSupabaseMemoryRetriever` for retrieval. Use the Python ingestion pipeline and hardened Supabase functions for durable ingestion rather than relying on canvas-side writes for canonical memory.

## Manual Canvas Rebuild Checklist

### 1. Create The Shell

1. Open `http://localhost:7860`.
2. Create a new flow in the Starter Project.
3. Set the canvas zoom around `70-80%` so the full left-to-right chain is visible.
4. Place nodes in this order:

```text
Read File / Split Text / Local Hugging Face Embeddings
        -> LifeOSSupabaseMemoryRetriever

Chat Input
  -> Sovereign Intent Router
  -> OpenRouter
  -> LifeOSProtocolGate
  -> Context Funnel (Compressor)
  -> Agentic Orchestrator
  -> Chat Output
```

### 2. Rebuild The Old Visible Inputs

1. Add `Chat Input`.
2. Add `Sovereign Intent Router`.
3. Configure `Sovereign Intent Router`:
   - `Local LLM API URL`: `http://host.docker.internal:11434/v1` if using host Ollama from inside Docker.
   - `Routing Model`: `llama3:latest`
   - output should be a 4-Pillar routing manifest.
4. Connect:

```text
Chat Input.message -> Sovereign Intent Router.user_chat_input
```

5. Add `OpenRouter`.
6. Configure `OpenRouter`:
   - API key from Langflow secret/env input only.
   - Model may start as `openrouter/free`, then be replaced with the preferred production model.
7. Connect:

```text
Chat Input.message -> OpenRouter.input
Sovereign Intent Router.routing_manifest -> OpenRouter.system_message
```

### 3. Rebuild The Source/Chunking Rail

Use this rail for manual source preparation and testing only. Canonical ingestion should still go through the hardened Python/Supabase pipeline.

1. Add `Read File`.
2. Upload the approved source file only.
3. Add `Split Text`.
4. Configure `Split Text`:
   - `Chunk Size`: `1000` if recreating the screenshot exactly.
   - Preferred LifeOS canonical target: roughly `250` words with `10-15%` overlap.
   - `Chunk Overlap`: screenshot shows `150`.
   - `Separator`: blank-line paragraph separator.
5. Connect:

```text
Read File.raw_content -> Split Text.input
```

### 4. Rebuild Embedding Contract

1. Add `Local Hugging Face Embeddings`.
2. Configure:

```text
sentence-transformers/all-MiniLM-L6-v2
```

3. Confirm every embedding path is `384` dimensions.
4. Do not use OpenAI `1536` dimension embeddings in this system.

### 5. Add Phase 2 Memory Retrieval

1. Add `LifeOSSupabaseMemoryRetriever`.
2. Configure:
   - `supabase_url`: `http://kong:8000`
   - `collections`: `lifeos_core`
   - `match_count`: `8`
   - `include_sensitive`: `false`
3. Connect:

```text
Chat Input.message -> LifeOSSupabaseMemoryRetriever.query
Sovereign Intent Router.routing_manifest.active_pillar -> LifeOSSupabaseMemoryRetriever.active_pillar
```

4. If the router emits uppercase pillars, normalize before storage/retrieval:

```text
DEEN -> deen
NAFS_AQL -> nafs_aql
MAAL -> maal
NASL_KHALQ -> nasl_khalq
```

5. Retrieval output:

```text
LifeOSSupabaseMemoryRetriever.memories -> Context Funnel.vector_results
```

### 6. Add Protocol 001 Gate

1. Add `LifeOSProtocolGate` between routing and orchestration.
2. Connect:

```text
Chat Input.message -> LifeOSProtocolGate.task
Sovereign Intent Router.routing_manifest.active_pillar -> LifeOSProtocolGate.active_pillar
```

3. Start with:

```text
estimated_ruin_risk = 0.0
```

4. Later replace `0.0` with a Planner/Critic numeric risk estimate.
5. Connect:

```text
LifeOSProtocolGate.gate -> Context Funnel.protocol_status
LifeOSProtocolGate.gate -> Agentic Orchestrator.preflight_gate
```

6. Required behavior:
   - `estimated_ruin_risk > 0.05` blocks execution.
   - Financial, external, destructive, or client-facing actions require explicit approval.
   - Blocked actions must go to audit.

### 7. Rebuild Context Funnel

1. Add `Context Funnel (Compressor)`.
2. Configure/accept inputs:

```text
Sovereign Intent Router.routing_manifest -> Context Funnel.route_manifest_json
LifeOSSupabaseMemoryRetriever.memories -> Context Funnel.vector_results
LifeOSProtocolGate.gate -> Context Funnel.protocol_status
```

3. Recreate the four visible pillar lanes from the screenshot:

```text
Deen Layer Data
Nafs/Aql Layer Data
Maal Layer Data
Nasl/Khalq Layer Data
```

4. Context Funnel output:

```text
Context Funnel.context_anchor -> Agentic Orchestrator.context_anchor
```

### 8. Rebuild Agentic Orchestrator

1. Add `Agentic Orchestrator`.
2. Configure:
   - `Effort Budget`: `3 - Balanced`
   - `LLM API Base URL`: `https://openrouter.ai/api/v1`
   - API key from Langflow secret/env input only.
   - Main model can begin with the screenshot model, then be upgraded.
3. Connect:

```text
OpenRouter.model_response -> Agentic Orchestrator.user_task
Context Funnel.context_anchor -> Agentic Orchestrator.context_anchor
LifeOSProtocolGate.gate -> Agentic Orchestrator.preflight_gate
```

4. Enforce:
   - no external side effect unless `LifeOSProtocolGate.blocked=false`
   - no financial/client/destructive action unless explicit approval is present

### 9. Rebuild Output And Audit

1. Add `Chat Output`.
2. Connect:

```text
Agentic Orchestrator.final_approved_output -> Chat Output.input
```

3. Add `LifeOSAuditLogger`.
4. Connect:

```text
LifeOSProtocolGate.gate -> LifeOSAuditLogger.payload_json
Agentic Orchestrator.trace -> LifeOSAuditLogger.payload_json
```

5. Configure audit:
   - `event_type`: `langflow.run`
   - `source`: `langflow`
   - `consent_level`: from gate
   - `protocol_flags`: from gate/orchestrator

### 10. Minimum Smoke Test

1. In Playground, send:

```text
Summarize the LifeOS memory architecture and identify the active pillar.
```

2. Confirm:
   - router returns one of the four pillars
   - retriever returns safe `lifeos_core` memories
   - protocol gate returns non-blocked for low-risk summary requests
   - context funnel receives route manifest, memories, and protocol status
   - orchestrator produces final output
   - audit logger writes a `langflow.run` event

3. Then test a risky Maal prompt:

```text
Send a paid offer to a client and commit the price now.
```

4. Confirm:
   - `LifeOSProtocolGate` blocks or escalates
   - orchestrator does not execute the action
   - audit includes `explicit_approval` or `protocol_001`
