# **System Architecture Specification: Shali Life OS Memory & Routing**

## **1\. Architectural Overview & Design Philosophy**

The Shali Life OS represents the production-grade evolution of the "Memory OS v5" framework. It is engineered as a local-first, multi-agent orchestration system that prioritizes data sovereignty, persistent digital "brain" state, and high-performance semantic retrieval.

The system utilizes a **Serverless Hybrid Pipeline** to solve the latency-privacy trade-off. Computationally expensive tasks—Speech-to-Text (Whisper Large V3) and LLM Inference (Llama 3.1 8B)—are offloaded to Groq’s LPU acceleration via secure APIs, achieving sub-second response times. Conversely, Voice Activity Detection (VAD), Text-to-Speech (TTS), and the primary Vector Database (ChromaDB) remain local. The transition from the unstable Streamlit architecture to a **PyQt5-based Workstation UI** provides the stateful persistence required for background memory processing and real-time multi-agent routing.

\--------------------------------------------------------------------------------

## **2\. Deliverable 1 (D1): Memory Schema & Data Structuring**

### **2.1 ChromaDB Metadata Schema Definition**

To ensure accurate Retrieval-Augmented Generation (RAG) and prevent cross-agent amnesia, all vectorized entries must adhere to this formal schema:

{  
  "pillar": "string",  
  "sub-topic": "string",  
  "temporal\_state": "string",  
  "cross\_pillar\_links": "array",  
  "entities\_aliases": "array",  
  "provenance\_date": "ISO-8601 string",  
  "confidence\_score": "float"  
}

| Key | Data Type | Functional Purpose |
| :---- | :---- | :---- |
| `pillar` | String | Defines the primary domain (Deen, Vessel, Stewardship, Web) used for high-level routing. |
| `sub-topic` | String | Specific agent-level category (e.g., Coding, Finance, Medical) for granular retrieval. |
| `temporal_state` | String | Flags relevance: `active_memory` (current), `historical` (archival), or `deprecated` (ignored). |
| `cross_pillar_links` | Array | IDs connecting related concepts across silos (e.g., linking a "Client" to "Finance"). |
| `entities_aliases` | Array | Synonyms for entities to increase semantic hit rates during keyword mismatch. |
| `provenance_date` | String | Timestamp used by the Orchestrator to calculate time-based memory decay. |
| `confidence_score` | Float | The initial reliability weight, defaulting to a baseline of 0.5 (Source E003200). |

### **2.2 Semantic Chunking Strategy**

The system mandates a **250-word block** strategy. This block size is mathematically optimized to ensure semantic density—providing the LLM with sufficient context to "understand" the fragment—while remaining compatible with the Llama 3.1 8B context window (131,071 tokens).

**Technical Implementation Note:** All segmentation must employ a **10-15% Overlapping Chunk protocol**. This is specifically designed to mitigate "Boundary Loss," ensuring that semantic entities or critical data points are not bisected by the chunking algorithm, thereby maintaining contextual continuity across indices.

\--------------------------------------------------------------------------------

## **3\. Deliverable 2 (D2): Langflow Smart Router Configuration**

### **3.1 Natural Language Routing Rules for the 4 Pillars**

The Shali OS categorizes its specialized agents into four parent Pillars. The Smart Router evaluates user intent to direct the query to the correct domain.

| Pillar Name | Semantic Keywords/Intent | Sample Query Routing Rule | Associated Agents |
| :---- | :---- | :---- | :---- |
| **Deen** | Spiritual, prayer, ethics, faith, growth. | "If the query involves spiritual growth, prayer, or ethics, route to Deen." | General, Research |
| **Vessel** | Health, fitness, routine, biological maintenance. | "If the user mentions physical health, fitness, or biological routine, route to Vessel." | Medical |
| **Stewardship** | Finance, management, productivity, tasks, clients. | "If the query involves finance, task management, or resource allocation, route to Stewardship." | Finance, Client, Automation, Coding |
| **Web** | Research, browsing, search, external data. | "If the request requires external research or web-based info gathering, route to Web." | Research, Voice |

### **3.2 Temporal Filtering & Memory State Logic**

The system implements a chronological ranking system to ensure the LLM prioritizes fresh data without losing historical context.

1. **Temporal Priority:** During the `rank_memories` phase, `active_memory` entries are given a higher weight for immediate context.  
2. **Memory Decay Mechanism:** The system utilizes a **Decay Constant**. The final retrieval score is calculated as `score -= age_in_days * 0.02`. This ensures semantic relevance is always tempered by chronological freshness (Source E003200).  
3. **Historical Retention:** Entries tagged as `historical` are retained for long-term RAG but are ranked lower than active entries unless a direct semantic match is found.  
4. **Baseline Weighting:** All new memories start at a `confidence_score` of 0.5, which is then adjusted based on user feedback and frequency of retrieval.

\--------------------------------------------------------------------------------

## **4\. Orchestration & Retrieval Flow**

### **4.1 The "Traffic Cop" Nervous System**

The `orchestrator.py` module manages the 8-step `process_input` loop.

1. **Select Persona:** Identify agent persona (e.g., Coding, Finance) via intent vectors.  
2. **Dual-Lookup Retrieval:** Search both the **Agent-Specific Database** and the **General Database** simultaneously to eliminate the "Silo Effect" amnesia (Source E003242).  
3. **Rank Memories:** Apply temporal decay and confidence scores to filter the top 5 results.  
4. **Build Context:** Synthesize ranked memories into a clean context string.  
5. **Tool Check:** Scan input for keywords (e.g., "create file") to trigger `automation.py`.  
6. **Execute Agent:** Send the system prompt, context, and input to the Groq LLM Client.  
7. **Memory Injection:** Asynchronously store the user input and AI response back to ChromaDB.  
8. **UI Return:** Deliver the final response to the PyQt5 interface worker thread.

**Critical Implementation Note:** To prevent the `c10.dll` initialization crash on Windows, the system mandates a strict **Import Order**. The `orchestrator.py` (which initializes PyTorch/Torch) **must** be loaded before the PyQt5 UI libraries (Source E003190).

### **4.2 Security & Vault Protocol Integration**

Metadata tagged as "Sensitive" or "Passwords" is protected by the **Conscious Security Lock**.

**\[INFO\] 2-Step Verification:** If the Orchestrator identifies a request for sensitive data (via metadata tag), it is instructed to pause. The system shall only release this context if the user provides the **Master PIN (7777) or (7788)**  within the query string (e.g., "What is my password? PIN 7788"). This forces the LLM to verify the PIN before the data is injected into the context window (Source E003250).

\--------------------------------------------------------------------------------

## **5\. Architectural Decision Records (ADR)**

| Decision | Source Context Index | Rationale |
| :---- | :---- | :---- |
| **250-word Chunking** | \[E002654\] | Optimal balance of semantic retrieval accuracy and Llama 3.1 token efficiency. |
| **PyQt5 Desktop UI** | \[E003184\] | Replaces Streamlit to provide stateful persistence and prevent script-rerun instability. |
| **Threaded Worker Model** | \[E003241\] | Decouples the UI from the LLM client, ensuring the interface remains responsive while the agent "thinks." |
| **Multi-Agent Silos** | \[E003255\] | Isolates client-specific data (e.g., "Violet" vs. "Mahmoud") to prevent context bleed across projects. |

\--------------------------------------------------------------------------------

## **6\. Deployment & Start-up Protocol**

### **6.1 One-Click Execution (Boot\_OS.bat)**

To bypass the stability issues of Python 3.14 (specifically with PyTorch DLLs), the system must be isolated in a **Python 3.11 Virtual Environment**. The following `.bat` file ensures the environment is activated before the OS initializes.

@echo off  
:: Navigate to project directory  
cd /d "D:\\Shali-ai-brain\\MemoryOS\_v5"  
:: Activate isolated Python 3.11 environment  
call venv\\Scripts\\activate  
:: Launch system through the main bootloader  
python main.py  
pause

**Implementation Note:** The use of `call venv\Scripts\activate` is mandatory to ensure all dependencies, including Torch and ChromaDB, are loaded from the isolated environment rather than the potentially unstable global site-packages (Source E003188, E003239).

