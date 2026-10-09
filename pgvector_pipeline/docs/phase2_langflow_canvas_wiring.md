# Phase 2 Langflow Canvas Wiring

This guide is intentionally manual. Do not edit Langflow flow JSON blindly; the running container did not expose a plain flow JSON file in `/app/langflow`, and the current component index had not yet registered LifeOS components.

## Component Availability

The component file is:

```text
D:\LifeOS\lifeos_memory\langflow_components\lifeos_supabase_memory.py
```

It has been copied into the running container at:

```text
/app/data/lifeos_components/lifeos_supabase_memory.py
```

The import-tested component class names are:

```text
LifeOSSupabaseMemoryRetriever
LifeOSProtocolGate
LifeOSAuditLogger
```

For future restarts, the compose contract now sets:

```text
LANGFLOW_COMPONENTS_PATH=/app/data/lifeos_components
SUPABASE_URL=http://kong:8000
LIFEOS_DLP_MODE=true
```

You must also provide:

```text
SUPABASE_SERVICE_ROLE_KEY=<local service role key>
```

## If Components Do Not Appear In The Palette

Use one of these safe paths:

1. Restart Langflow with the updated compose file so `LANGFLOW_COMPONENTS_PATH` is indexed.
2. Or add a Langflow **Custom Component** node and paste the contents of `lifeos_supabase_memory.py`.

Do not hand-edit the canvas JSON.

## Intended Wiring

### Retrieval Path

1. Drag `LifeOSSupabaseMemoryRetriever` onto the canvas before the Context Funnel.
2. Connect the existing `Chat Input` message output to:

```text
LifeOSSupabaseMemoryRetriever.query
```

3. Connect the active pillar output from the intent classifier/router to:

```text
LifeOSSupabaseMemoryRetriever.active_pillar
```

If the classifier emits uppercase values, use:

```text
DEEN | NAFS_AQL | MAAL | NASL_KHALQ
```

4. Set `collections` manually or from the Smart Router:

```text
lifeos_core
```

For client workspaces, pass a CSV such as:

```text
client_mahmoud,lifeos_core
```

5. Keep defaults:

```text
supabase_url = http://kong:8000
match_count = 8
include_sensitive = false
```

6. Connect:

```text
LifeOSSupabaseMemoryRetriever.memories
  -> Context Funnel.vector_results
```

The retriever uses local `sentence-transformers/all-MiniLM-L6-v2`, generates a 384-dim query embedding, then calls `match_life_memories` through Supabase PostgREST.

### Protocol 001 Gate Path

1. Drag `LifeOSProtocolGate` before the Agentic Orchestrator.
2. Connect:

```text
Chat Input.message -> LifeOSProtocolGate.task
Intent Classifier.active_pillar -> LifeOSProtocolGate.active_pillar
```

3. For `estimated_ruin_risk`, start with a fixed low value:

```text
0.0
```

Then replace it with a Planner/Critic risk estimate once that node emits numeric risk.

4. Connect:

```text
LifeOSProtocolGate.gate -> Context Funnel.protocol_status
LifeOSProtocolGate.gate -> Agentic Orchestrator.preflight_gate
```

5. Orchestrator behavior:

```text
blocked=true
  -> stop execution, ask for explicit approval

consent_level=explicit_approval
  -> draft only, no external/financial/destructive action

protocol_flags includes protocol_001
  -> write audit entry and halt
```

### Recommended Canvas Shape

```text
Chat Input
  |-> Protocol 508 Intent Classifier
  |     |-> Smart Router.collections
  |     |-> LifeOSSupabaseMemoryRetriever.active_pillar
  |     `-> LifeOSProtocolGate.active_pillar
  |-> LifeOSSupabaseMemoryRetriever.query
  `-> LifeOSProtocolGate.task

LifeOSSupabaseMemoryRetriever.memories
  -> Context Funnel.vector_results

LifeOSProtocolGate.gate
  -> Context Funnel.protocol_status
  -> Agentic Orchestrator.preflight_gate

Context Funnel.context_anchor
  -> Agentic Orchestrator.context_anchor

Chat Input.message
  -> Agentic Orchestrator.user_task

Agentic Orchestrator.final
  -> Chat Output
```

### Audit Logger

Use `LifeOSAuditLogger` after the gate and after orchestrator completion:

```text
LifeOSProtocolGate.gate -> LifeOSAuditLogger.payload_json
Agentic Orchestrator.trace -> LifeOSAuditLogger.payload_json
```

Set:

```text
event_type = langflow.run
protocol_flags = comma-separated flags from gate/orchestrator
consent_level = gate.consent_level
```

The audit table is append-only. The UI added in Phase 2 is read-only and does not expose approval mutations.
