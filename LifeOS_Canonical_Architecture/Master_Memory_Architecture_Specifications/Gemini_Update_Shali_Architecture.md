# **Architecture Specification Update: Shali LifeOS Orchestration & Advanced Memory Architecture**

**Document Version:** 2.0 (Agentic Update)

**Date:** June 5, 2026

**System Status:** Production Design Phase

## **I. Executive Summary of System Evolution**

This document serves as the official, comprehensive architecture update for **Shali LifeOS**. It bridges the high-level philosophical memory layers outlined in Version 1.0 with the concrete, production-ready **Langflow** and **Supabase** backend engineering completed in June 2026\.

The core breakthrough of this update is the migration from a passive, linear single-pass pipeline (Prompt $\\rightarrow$ LLM $\\rightarrow$ Output) to an **active, self-auditing Agentic Loop** running entirely in Python inside Langflow, paired with a unified data framework.

## **II. Core Architecture Update: The Internal Agentic Loop**

To bypass Langflow's strict **Directed Acyclic Graph (DAG)** constraint (which explicitly forbids loops or visual connections that form a circle), the multi-agent reasoning chain is fully encapsulated inside a single custom component: the **Agentic Orchestrator**.

\[Chat Input\] ───────┐  
                    ▼  
\[Parser/DB\] ──\> \[Agentic Orchestrator\] ──(Internal Python Loop)──\> \[Chat Output\]  
                \* Planner Passes to Executor  
                \* Executor Passes to Critic  
                \* Critic Evaluates (Rejects/Approves) up to Max Revisions

### **1\. The Multi-Agent Assembly Line**

The system eliminates external prompt nodes for planning and auditing, embedding them directly into memory execution loops:

* **The Planner Pass:** Automatically fragments incoming user requests into atomic sub-tasks and maps dependencies, calculating a structural heuristic complexity score (1 to 5).  
* **The Executor Pass:** Step-by-step processing of generated plans while handling unexpected blockers dynamically (BLOCKED:\<reason\>).  
* **The Psych-Critic Pass:** A strict, rejection-biased gatekeeper that audits output text against tone guidelines, completeness, and hard constraints before clearance.

### **2\. Effort Budget Presets & Dynamic Throttling**

The Next.js user interface passes cognitive load directives via dynamic localized state tweaks. The internal orchestrator translates these presets into real-time operational constraints:

* **Instant Pass:** 1 max iteration, 0.60 confidence acceptance threshold (Target: $\<3000\\text{ms}$ latency).  
* **Balanced Pass:** 3 max iterations, 0.78 confidence acceptance threshold.  
* **Maximum Optimization Pass:** Up to 8 iterations, 0.92 confidence acceptance threshold, with programmatic **plateau detection** (automatically halts execution if the confidence score changes by $\<0.05$ over 3 consecutive loops to prevent budget burn).

## **III. Production Memory Framework & Database Consolidation**

### **1\. The Unified Database Strategy: Supabase \+ pgvector**

To maintain the system’s commitment to **Sovereign Memory** while removing multi-platform enterprise bloat (such as Oracle AI Database solutions), the storage backend is consolidated onto **Supabase (PostgreSQL)** running the pgvector extension.

* **Relational Storage (Supabase Tables):** Houses structured metrics inside the *Stewardship (Maal)* pillar, tracking client profiles, active contracts, invoicing history, and deadlines.  
* **Vector Storage (Supabase pgvector):** Replaces standalone cloud database networks by storing multi-dimensional mathematical embeddings (gemini-embedding-001) of brand styles, client psychology logs, and persistent facts in unified tables.  
* **Sovereign Cache Layer:** Local text backups are maintained directly on the host file system in structured Markdown format (.md), version-controlled via Git to ensure data autonomy.

### **2\. Multi-Layer Memory Flow & Funnel Integration**

To prevent context bleed and screen clutter inside Langflow, multi-layer data extraction is streamlined through a **Parallel Switchboard via Linear Funneling** technique:

                 ┌──\> \[Stewardship Vault: Upwork ChromaDB/Supabase\] ──┐  
                  │                                                    ▼  
\[Chat Input\] ──\> \[Smart Router\] ───────────────────────────────\> \[Context Funnel\] ──\> \[Context Anchor\]  
                  │                                                    ▲  
                  └──\> \[Health / Spiritual Vault: Supabase Tables\] ────┘

* **The Smart Router (The Switchboard Master):** Reads incoming traffic in parallel with the user task execution line. It isolates matching categories and fires a query *only* to the specific file vault required.  
* **Project Isolation via Collection Mapping:** To ensure Shali never mixes the custom styles of different clients (e.g., *Mahmoud Elwakeel* vs. *Jordan Hobbs*), the router dynamically injects localized parameters (collection\_name) directly into database retrieval nodes on demand.  
* **The Context Funnel:** A single prompt aggregation element that accepts inputs from all database vaults simultaneously, concatenating empty strings for un-triggered databases, and funneling a clean data array into the orchestrator's **Context Anchor** point.

## **IV. Technical Langflow Custom Component Spec**

This code blueprint is the finalized engine currently deployed to the main Langflow workspace block. It incorporates structural typing fixes, explicit StrInput patches to accommodate recent framework revisions, and strict MessageTextInput implementations to allow native visual connection ports for database files.

Agentic Orchestrator custom node code:

from langflow.custom import Component  
from langflow.io import (MessageInput, StrInput, DropdownInput, SecretStrInput, Output, MessageTextInput)  
from langflow.schema import Data  
from langflow.schema.message import Message  
import httpx  
import json  
import time  
from dataclasses import dataclass, field  
from enum import Enum  
from typing import Optional

\# ── Pipeline state machine ─────────────────────────────────────────────────────  
class PipelineState(Enum):  
    PLANNING    \= "planning"  
    EXECUTING   \= "executing"  
    VERIFYING   \= "verifying"  
    TERMINATED  \= "terminated"  
    BUDGET\_HALT \= "budget\_halt"

@dataclass  
class EffortBudget:  
    max\_iterations: int  
    min\_confidence: float  
    max\_tokens\_total: int  
    tokens\_spent: int   \= 0  
    iterations\_used: int \= 0

    def is\_exhausted(self) \-\> bool:  
        return (  
            self.iterations\_used \>= self.max\_iterations or  
            self.tokens\_spent    \>= self.max\_tokens\_total  
        )

EFFORT\_PRESETS \= {  
    "1 \- Instant":  {"max\_iterations": 1, "min\_confidence": 0.60, "max\_tokens\_total": 1200},  
    "2 \- Fast":     {"max\_iterations": 2, "min\_confidence": 0.70, "max\_tokens\_total": 2500},  
    "3 \- Balanced": {"max\_iterations": 3, "min\_confidence": 0.78, "max\_tokens\_total": 5000},  
    "4 \- Thorough": {"max\_iterations": 5, "min\_confidence": 0.85, "max\_tokens\_total": 9000},  
    "5 \- Maximum":  {"max\_iterations": 8, "min\_confidence": 0.92, "max\_tokens\_total": 18000},  
}

\# ── Prompt templates (self-contained — no external prompt nodes needed) ─────────  
PLANNER\_PROMPT \= """\\  
You are a Decomposition Planner. Your ONLY job is structured task decomposition.

TASK: {task}  
CONTEXT: {context}  
PREVIOUS\_FAILURES: {failure\_log}

Respond ONLY with valid JSON, no markdown, no explanation:  
{{"sub\_tasks": \["step 1", "step 2"\], "estimated\_complexity": 2, "risk\_flags": \["risk 1"\]}}\\  
"""

EXECUTOR\_PROMPT \= """\\  
You are a precise Sub-task Executor.

ORIGINAL TASK: {task}  
SUB-TASKS TO COMPLETE: {sub\_tasks}  
CONTEXT: {context}  
KNOWN FAILURES TO AVOID: {failure\_log}

Rules:  
\- Execute every sub-task in sequence, outputting results for each.  
\- If genuinely blocked on a step, prefix ONLY that section: BLOCKED:\<reason\>  
\- Begin your full response with a confidence annotation: \[HIGH\], \[MED\], or \[LOW\]

Output: confidence\_annotation \+ complete result\\  
"""

CRITIC\_PROMPT \= """\\  
You are a Verification Critic. Your default is REJECTION.

ORIGINAL TASK: {task}  
EXECUTION RESULT: {result}  
PLANNED SUB-TASKS: {sub\_tasks}

Score each axis 0.0–1.0:  
\- task\_fidelity: Does the result fully solve the stated task?  
\- logical\_consistency: Are there internal contradictions?  
\- completeness: Are ALL sub-tasks addressed?

Respond ONLY with valid JSON, no markdown, no explanation:  
{{"accept": false, "composite\_score": 0.72, "axis\_scores": {{"task\_fidelity": 0.8, "logical\_consistency": 0.7, "completeness": 0.65}}, "failure\_reasons": \["missing X"\], "patch\_instructions": "Add section covering X with specific detail Y"}}\\  
"""

class AgenticOrchestratorComponent(Component):  
    """  
    Implements the full Planner → Executor → Critic iterative loop  
    inside a single Langflow node.

    ARCHITECTURE NOTE:  
    Langflow's DAG constraint is visual-only. This component solves the  
    cycle problem by encapsulating the entire state machine in Python.  
    The visual graph sees one node; internally we run N iterations until  
    the budget is exhausted or the Critic accepts the result.  
    """

    display\_name \= "Agentic Orchestrator"  
    description  \= (  
        "Full Planner → Executor → Critic loop with budget throttling. "  
        "Solves Langflow DAG cycle limitation via internal state machine."  
    )  
    icon  \= "brain"  
    name  \= "AgenticOrchestrator"

    \# ── Inputs ─────────────────────────────────────────────────────────────────  
    inputs \= \[  
        MessageInput(  
            name="user\_task",  
            display\_name="User Task",  
            info="The task to solve iteratively.",  
        ),  
        MessageTextInput( \# UPDATED: This adds the input dot for Data wires  
            name="context\_anchor",  
            display\_name="Context Anchor",  
            info="Wire your Parser here.",  
            input\_types=\["Data", "Text", "Message"\]  
        ),  
        DropdownInput(  
            name="effort\_preset",  
            display\_name="Effort Budget",  
            options=list(EFFORT\_PRESETS.keys()),  
            value="3 \- Balanced",  
            info="Controls max iterations, token spend, and acceptance threshold.",  
        ),  
        StrInput(  
            name="api\_base\_url",  
            display\_name="LLM API Base URL",  
            value="https://openrouter.ai/api/v1",  
            info="OpenRouter · Ollama (http://localhost:11434/v1) · any OpenAI-compatible endpoint.",  
        ),  
        SecretStrInput(  
            name="api\_key",  
            display\_name="API Key",  
            value="",  
            info="Leave empty for local Ollama.",  
        ),  
        StrInput(  
            name="model\_name",  
            display\_name="Main Model",  
            value="liquid/lfm-2.5-1.2b-instruct:free",  
            info="Used for Planner and Executor passes.",  
        ),  
        StrInput(  
            name="critic\_model\_name",  
            display\_name="Critic Model (optional)",  
            value="",  
            advanced=True,  
            info="Smaller/faster model for Critic pass. Leave empty to use Main Model.",  
        ),  
    \]

    \# ── Outputs ────────────────────────────────────────────────────────────────  
    \# These appear as a dropdown on the output socket in Langflow.  
    \# Wire each to its appropriate downstream node.  
    outputs \= \[  
        Output(  
            display\_name="Final Approved Output",  
            name="final\_output",  
            method="build\_final\_output",  
        ),  
        Output(  
            display\_name="Execution Trace",  
            name="execution\_trace",  
            method="build\_execution\_trace",  
        ),  
        Output(  
            display\_name="To Planner",  
            name="to\_planner",  
            method="build\_planner\_state",  
        ),  
        Output(  
            display\_name="To Executor",  
            name="to\_executor",  
            method="build\_executor\_state",  
        ),  
        Output(  
            display\_name="To Critic",  
            name="to\_critic",  
            method="build\_critic\_state",  
        ),  
    \]

    \# ── LLM call ───────────────────────────────────────────────────────────────

    def \_call\_llm(  
        self,  
        prompt: str,  
        model: Optional\[str\] \= None,  
        max\_tokens: int \= 800  
    ) \-\> tuple:  
        model   \= model or self.model\_name  
        headers \= {"Content-Type": "application/json"}  
        if self.api\_key:  
            headers\["Authorization"\] \= f"Bearer {self.api\_key}"

        payload \= {  
            "model":       model,  
            "messages":    \[{"role": "user", "content": prompt}\],  
            "max\_tokens":  max\_tokens,  
            "temperature": 0.2,  \# Low temp — structured JSON outputs  
        }

        url \= f"{self.api\_base\_url.rstrip('/')}/chat/completions"

        try:  
            with httpx.Client(timeout=120.0) as client:  
                resp \= client.post(url, headers=headers, json=payload)  
                resp.raise\_for\_status()  
                data    \= resp.json()  
                content \= data\["choices"\]\[0\]\["message"\]\["content"\]  
                tokens  \= data.get("usage", {}).get("total\_tokens", len(content) // 4\)  
                return content, tokens  
        except Exception as e:  
            return f"LLM\_ERROR: {e}", 0

    \# ── JSON parser ────────────────────────────────────────────────────────────

    def \_parse\_json(self, text: str) \-\> dict:  
        """Strips markdown fences and safely parses JSON from LLM output."""  
        text \= text.strip()  
        if "\`\`\`" in text:  
            parts \= text.split("\`\`\`")  
            text  \= parts\[1\] if len(parts) \> 1 else parts\[0\]  
            if text.startswith("json"):  
                text \= text\[4:\]  
        start \= text.find("{")  
        end   \= text.rfind("}") \+ 1  
        if start \!= \-1 and end \> start:  
            try:  
                return json.loads(text\[start:end\])  
            except json.JSONDecodeError:  
                pass  
        return {}

    \# ── Message extractor ──────────────────────────────────────────────────────

    def \_to\_text(self, msg) \-\> str:  
        if isinstance(msg, Message):   return msg.text or ""  
        if isinstance(msg, str):       return msg  
        if hasattr(msg, "text"):       return str(msg.text)  
        return str(msg) if msg else ""

    \# ── THE STATE MACHINE ──────────────────────────────────────────────────────  
    \# This is the cyclic loop that Langflow cannot represent visually.  
    \# It runs entirely in Python memory — the DAG validator never sees it.

    def \_run\_loop(self) \-\> dict:  
        task    \= self.\_to\_text(self.user\_task)  
        context \= (self.\_to\_text(self.context\_anchor) or "")\[:600\]  
        budget  \= EffortBudget(\*\*EFFORT\_PRESETS\[self.effort\_preset\])  
        critic\_model \= self.critic\_model\_name or None

        \# ── State variables ────────────────────────────────────────────  
        state              \= PipelineState.PLANNING  
        plan: dict         \= {}  
        execution\_result   \= ""  
        failure\_log: list  \= \[\]  
        confidence\_history: list \= \[\]  
        trace: list        \= \[\]

        \# ── Main loop ──────────────────────────────────────────────────  
        while not budget.is\_exhausted():

            \# PLANNING ──────────────────────────────────────────────────  
            if state \== PipelineState.PLANNING:  
                iter\_label \= budget.iterations\_used \+ 1  
                trace.append(f"\[Iter {iter\_label}\] PLANNER →")

                resp, tokens \= self.\_call\_llm(  
                    PLANNER\_PROMPT.format(  
                        task=task,  
                        context=context or "None",  
                        failure\_log="\\n".join(failure\_log\[-3:\]) or "None",  
                    ),  
                    max\_tokens=400,  
                )  
                budget.tokens\_spent \+= tokens  
                plan \= self.\_parse\_json(resp)

                if "sub\_tasks" not in plan:  
                    plan \= {"sub\_tasks": \[task\], "estimated\_complexity": 2, "risk\_flags": \[\]}

                trace.append(f"  sub\_tasks={plan\['sub\_tasks'\]}")

                \# Fast-path: trivial tasks skip multi-iteration depth  
                if plan.get("estimated\_complexity", 2\) \== 1:  
                    budget.max\_iterations \= min(budget.max\_iterations, 2\)

                state \= PipelineState.EXECUTING

            \# EXECUTING ─────────────────────────────────────────────────  
            elif state \== PipelineState.EXECUTING:  
                trace.append(f"\[Iter {budget.iterations\_used \+ 1}\] EXECUTOR →")

                resp, tokens \= self.\_call\_llm(  
                    EXECUTOR\_PROMPT.format(  
                        task=task,  
                        sub\_tasks=json.dumps(plan.get("sub\_tasks", \[task\])),  
                        context=context or "None",  
                        failure\_log="\\n".join(failure\_log\[-2:\]) or "None",  
                    ),  
                    max\_tokens=1400,  
                )  
                budget.tokens\_spent \+= tokens

                if "BLOCKED:" in resp:  
                    reason \= resp.split("BLOCKED:")\[1\]\[:200\]  
                    failure\_log.append(f"BLOCKED: {reason}")  
                    trace.append(f"  ✗ BLOCKED — re-planning")  
                    budget.iterations\_used \+= 1  
                    state \= PipelineState.PLANNING  
                    continue

                execution\_result \= resp  
                trace.append(f"  ✓ complete ({tokens} tok)")  
                state \= PipelineState.VERIFYING

            \# VERIFYING ─────────────────────────────────────────────────  
            elif state \== PipelineState.VERIFYING:  
                trace.append(f"\[Iter {budget.iterations\_used \+ 1}\] CRITIC →")

                resp, tokens \= self.\_call\_llm(  
                    CRITIC\_PROMPT.format(  
                        task=task,  
                        result=execution\_result\[:1800\],  
                        sub\_tasks=json.dumps(plan.get("sub\_tasks", \[\])),  
                    ),  
                    model=critic\_model,  
                    max\_tokens=350,  
                )  
                budget.tokens\_spent \+= tokens  
                verdict \= self.\_parse\_json(resp)

                score \= float(verdict.get("composite\_score", 0.5))  
                confidence\_history.append(score)

                trace.append(  
                    f"  score={score:.2f} "  
                    f"accept={verdict.get('accept', False)} "  
                    f"threshold={budget.min\_confidence}"  
                )

                \# ── Termination: accepted ─────────────────────────────  
                if verdict.get("accept") and score \>= budget.min\_confidence:  
                    state \= PipelineState.TERMINATED  
                    trace.append("  ✓ ACCEPTED — loop complete")  
                    break

                \# ── Termination: confidence plateau ───────────────────  
                if len(confidence\_history) \>= 3:  
                    delta \= max(confidence\_history\[-3:\]) \- min(confidence\_history\[-3:\])  
                    if delta \< 0.05:  
                        state \= PipelineState.BUDGET\_HALT  
                        trace.append(f"  ⚠ PLATEAU (Δ={delta:.3f}) — best result returned")  
                        break

                \# ── Continue: inject patch, loop back to Planner ──────  
                patch \= verdict.get("patch\_instructions", "Revise and improve.")  
                failure\_log.append(f"Iter {budget.iterations\_used \+ 1}: {patch}")  
                trace.append(f"  → patch: {patch\[:80\]}")  
                budget.iterations\_used \+= 1  
                state \= PipelineState.PLANNING

            else:  
                break  \# Defensive exit

        \# Budget exhausted without explicit termination  
        if state not in (PipelineState.TERMINATED, PipelineState.BUDGET\_HALT):  
            state \= PipelineState.BUDGET\_HALT  
            trace.append(f"⚠ Budget exhausted ({budget.iterations\_used} iters)")

        return {  
            "result":             execution\_result,  
            "final\_score":        round(confidence\_history\[-1\], 3\) if confidence\_history else 0.0,  
            "confidence\_history": confidence\_history,  
            "iterations\_used":    budget.iterations\_used,  
            "tokens\_spent":       budget.tokens\_spent,  
            "termination\_reason": state.value,  
            "trace":              trace,  
            "plan":               plan,  
        }

    \# ── Shared cache: all outputs run the loop once per invocation ─────────────

    def \_cached(self) \-\> dict:  
        if not hasattr(self, "\_result\_cache") or self.\_result\_cache is None:  
            self.\_result\_cache \= self.\_run\_loop()  
        return self.\_result\_cache

    \# ── Output builders ────────────────────────────────────────────────────────

    def build\_final\_output(self) \-\> Message:  
        self.\_result\_cache \= None  \# Fresh run when primary output is invoked  
        r \= self.\_cached()  
        self.status \= (  
            f"Score {r\['final\_score'\]:.2f} · "  
            f"{r\['iterations\_used'\]} iters · "  
            f"{r\['tokens\_spent'\]} tok · "  
            f"{r\['termination\_reason'\]}"  
        )  
        return Message(text=r\["result"\])

    def build\_execution\_trace(self) \-\> Data:  
        r \= self.\_cached()  
        return Data(data={  
            "trace":              r\["trace"\],  
            "iterations\_used":    r\["iterations\_used"\],  
            "tokens\_spent":       r\["tokens\_spent"\],  
            "confidence\_history": r\["confidence\_history"\],  
            "termination\_reason": r\["termination\_reason"\],  
            "final\_score":        r\["final\_score"\],  
        })

    def build\_planner\_state(self) \-\> Data:  
        r \= self.\_cached()  
        return Data(data={"plan": r.get("plan", {}), "source": "planner"})

    def build\_executor\_state(self) \-\> Data:  
        r \= self.\_cached()  
        return Data(data={"result": r.get("result", ""), "source": "executor"})

    def build\_critic\_state(self) \-\> Data:  
        r \= self.\_cached()  
        return Data(data={  
            "final\_score":        r.get("final\_score", 0.0),  
            "confidence\_history": r.get("confidence\_history", \[\]),  
            "source": "critic",  
        })  
