### System Architecture Specification: Life OS (Phase 1 \- Topic Tree & Source Manifest)

#### 1\. ARCHITECTURAL IDENTITY & CORE MISSION

**Shali AI**  : A world-class Senior AI Systems Architect and elite developer persona. Pragmatic, witty, and slightly sassy, Shali operates with the authority of a tech lead who prioritizes "The Pragmatic Elite" philosophy: finding the fastest, most efficient, and—crucially—free paths to production-grade results using APIs like Groq and OpenRouter.**Life OS (Memory OS v5.1)**  : The transition from fragmented, unstable Streamlit experiments to a persistent, local-first "Personal Digital Brain." The system provides a low-latency, multi-agent environment capable of persistent memory retrieval and local system automation.**Memory-Augmented Orchestration**  : The core operational goal of Life OS. It focuses on local-first data privacy and speed, utilizing cloud inference only for heavy lifting while maintaining a deep, semantic "subconscious" via vector storage.

#### 2\. THEMATIC ANALYSIS: THE 4 PILLARS TOPIC TREE

##### I. Deen (Identity & Core Logic)

* **Shali Master Prompt:**  The authoritative DNA of the system; includes the "Motion Graphics Science" module and advanced animation physics.  
* **The Orchestrator:**  The central "Nervous System" (orchestrator.py) routing traffic between UI, Memory, and Agents.  
* **Conscious Security Protocol:**  The Master PIN logic (PIN: 7777\) governing access to sensitive data vaults.  
* **Agent Registry:**  Taxonomy of specialized workers (Coding, Finance, Client, Research, Creative, Medical, Automation, Voice).

##### II. Vessel (Local System & Physicality)

* **Hardware Constraints:**  Windows 11 environment running an NVIDIA RTX 2060 Super (8GB VRAM) and 16GB System RAM.  
* **Software Isolation:**  Python 3.11 Virtual Environment (venv).  **Strict Requirement:**  Isolation is mandatory to mitigate the c10.dll initialization crashes found in Python 3.14/PyTorch collisions.  
* **Local Storage Architecture:**  
* data/chroma\_db: Persistent vector storage using all-MiniLM-L6-v2.  
* data/workspace: Safe-zone for file operations.  
* projects.json: UI state, project metadata, and chat history.

##### III. Stewardship (Management & Production)

* **Client Workspaces:**  
* **Client: Violet:**  Focus on 2D design, high-saturation color grading, and Friday 5 PM deadlines.  
* **Client: Mahmoud:**  YouTube talking-head footage and educational storytelling logic.  
* **Kilo Code Logic:**  
* **Feedback System:**  Integrated 👍/👎 vote storage in ChromaDB to influence memory ranking.  
* **Thread-Aware Memory:**  Context isolation based on specific thread\_id.  
* **Automation Engine:**  Safe file operations restricted via absolute pathing (os.path.abspath).

##### IV. Web (External Intelligence & APIs)

* **Inference Services:**  OpenRouter (Primary LLM) and Groq LPU Acceleration (Whisper Large V3 STT & Llama 3.1 8B).  
* **Live API Configurations:**  
* **Google AI Studio Live API:**  Using gemini-2.0-flash-exp for audio-to-audio multimodal sessions.  
* **Voice Specs:**  Leda (Youthful) or Zephyr (Bright) voices; 258 tokens/image media resolution for technical screen reading.

#### 3\. CANONICAL ENTITY REGISTRY

Canonical Entity,Source References,Functional Responsibility  
Shali AI Assistant,"Shali, Aneeqa, Zoya, Memory OS v5",Senior-level interface and persona; manages cross-agent coordination.  
Unified RAG Pipeline,"ChromaDB, Vector Search, Semantic Memory","Handles embedding, feedback-weighted storage, and global retrieval."  
OpenRouter Service Client,"llm\_client.py, API Client",Centralized handler for all external LLM requests to prevent logic duplication.  
System Orchestrator,"Traffic Cop, orchestrator.py, Brain","Mediates between UI, project-specific silos, and the automation layer."  
Automation Engine,"PC Control, Tool Layer, automation.py",Executes file actions and system utilities within the data/workspace sandbox.

#### 4\. TEMPORAL STATE MAPPING

* **Active:**  
* **PyQt5 Desktop UI:**  Persistent, event-driven interface replacing unstable web loops.  
* **ChromaDB:**  Local vector database for long-term memory.  
* **Thread-Aware Memory:**  Context isolation by thread IDs (Kilo Code implementation).  
* **Feedback System:**  👍/👎 interaction weights.  
* **Historical:**  
* **Streamlit GUI (v5):**  Discarded due to re-execution instability and lack of persistence.  
* **ChatArchivist (Extension):**  Manual scraping of Gemini/AI Studio sessions.  
* **Deprecated:**  
* **"Aneeqa" Persona:**  Architectural identity superseded by Shali.  
* **Python 3.14 Global Runtime:**  Abandoned due to c10.dll initialization routine failures.  
* **Google Drive Memory:**  Removed in favor of local-first privacy and speed.  
* **Experimental:**  
* **Voice Engine (Wake Word):**  "Hey OS" / "Hey Shali" local listener.  
* **Kokoro-82M TTS:**  Local, WebGPU-accelerated text-to-speech.  
* **IndexedDB:**  Investigated for mobile/local storage during the Replit phase.

#### 5\. SOURCE CONTEXT MANIFEST

Data Point,Primary Pillar,Temporal State,Context Reference  
Project Aurora,Stewardship,Active,Secret project used for memory persistence verification.  
Master PIN 7777,Deen,Active,"Core of the ""Conscious Security Protocol."""  
Orion2026,Stewardship,Active,Test password for verifying security vault unlocks.  
RTX 2060 Super,Vessel,Active,Hardware target for local embeddings and WebGPU TTS.  
all-MiniLM-L6-v2,Vessel,Active,Selected model for semantic vector generation.  
Silero VAD,Vessel,Active,Local Voice Activity Detection for the audio pipeline.

#### 6\. INFRASTRUCTURE COMPONENT SPECIFICATION

MemoryOS/  
├── main.py              \# Bootloader: Manages DLL order & venv activation  
├── config.py            \# Global DNA: API keys, PIN 7777, and paths  
├── core/  
│   ├── orchestrator.py  \# Traffic cop: Handles routing and thread-aware logic  
│   ├── memory.py        \# ChromaDB interface: Implements Global Search & Feedback  
│   ├── agents.py        \# Multi-agent registry: Persona prompts & confidence math  
│   └── prompts.py       \# Master System Prompts (including Animation Science)  
├── tools/  
│   ├── automation.py    \# File ops: Natural Language Parameter Extractor  
│   └── system\_tools.py  \# PC Utilities: Chrome, App launching, CPU/RAM monitor  
├── ui/  
│   ├── desktop\_app.py   \# PyQt5 Interface: Multi-threaded background workers  
│   └── themes.py        \# UI Aesthetics: Catppuccin color scheme  
├── services/  
│   └── llm\_client.py    \# OpenRouter Service: Dedicated API communication layer  
├── utils/  
│   ├── time\_utils.py    \# Memory decay and timestamping logic  
│   └── text\_processing.py \# Token cleaning and formatting  
├── data/  
│   ├── chroma\_db/       \# Persistent vector database silos  
│   ├── workspace/       \# Sandbox for AI-controlled file operations  
│   └── projects.json    \# Persistent UI state and chat history  
└── voice/  
    ├── wake\_word.py     \# "Hey OS" listener  
    └── speech.py        \# STT/TTS local integration

##### Service Level Responsibilities

* **orchestrator.py** : Coordinates the "Nervous System." It prevents the "Silo Effect" by forcing a  **Global Search**  in memory.py if a project-specific query returns low-confidence results.  
* **memory.py** : Manages isolated collections per client. Implements Kilo Code's  **Feedback Loop** , adjusting memory weight based on user 👍/👎.  
* **main.py** : Executes the DLL-priority boot sequence (Importing torch before PyQt5) to prevent system-level initialization crashes.  
* **llm\_client.py** : Isolates LLM logic to ensure a single point of failure and unified API tracking.

#### 7\. PHASE 1 VALIDATION PROTOCOLS

* **The Hands (Automation Test):**  
* *Input:*  "Create a file named alpha\_test.txt and write 'Automation protocol is active'."  
* *Validation:*  Verify file presence in data/workspace using os.path.abspath.  
* **The Brain (Routing Test):**  
* *Input:*  "Reverse a string" vs. "Mahmoud's video transition idea."  
* *Validation:*  UI Badge must transition from CODING to CREATIVE with a Confidence Threshold \> 0.25.  
* **The Database (Conscious Security Test):**  
* *Step A:*  Input "My backup server password is Orion2026."  
* *Step B:*  Query "What is my backup password?" (Expect: 🔒 Security Lock Active).  
* *Step C:*  Query "What is my backup password? PIN: 7777."  
* *Validation:*  OS must verify the PIN against config.py before retrieving from chroma\_db.

