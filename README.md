# Memory Operating System (MemoryOS)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Vector DB](https://img.shields.io/badge/Vector%20Store-ChromaDB%20%7C%20pgvector-orange.svg)](https://www.trychroma.com/)
[![TUI Framework](https://img.shields.io/badge/TUI-Textual-green.svg)](https://textual.textualize.io/)
[![GUI Framework](https://img.shields.io/badge/GUI-PyQt5%20%7C%20Streamlit-informational.svg)](https://riverbankcomputing.com/software/pyqt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A local-first cognitive operating system and multi-agent memory framework engineered for sovereign project execution, strict memory-bleed prevention, and dual-tier vector retrieval.

---

## Architectural Topology

```mermaid
graph TD
    subgraph UI_Layer["User Interfaces (God-Control Suite)"]
        TUI["Textual TUI (main.py)"]
        GUI["PyQt5 Desktop App (desktop_app.py)"]
        WebUI["Streamlit Dashboard (gui.py)"]
    end

    subgraph CoreBrain["Core Brain & Orchestration"]
        Router["Sovereign Router & Orchestrator"]
        ScopeGuard["Project Scope Guard (Zero Memory Bleed)"]
        Agents["Specialized Multi-Agent Mesh"]
        CommandCenter["Command Center (Planner, Analyzer, Ghost Detector)"]
    end

    subgraph MemoryTier["Dual-Tier Memory Storage"]
        ChromaStore["ChromaDB Local Store (SentenceTransformers all-MiniLM-L6-v2)"]
        PgvectorStore["Supabase pgvector Pipeline (Temporal Fusion Retriever)"]
        DLP["Data Loss Prevention & Secret Sanitizer"]
    end

    UI_Layer --> Router
    Router --> ScopeGuard
    ScopeGuard --> Agents
    Router --> CommandCenter
    Agents --> DLP
    DLP --> ChromaStore
    DLP --> PgvectorStore
```

---

## Key Capabilities

### 1. Zero-Bleed Project Isolation
- Enforces cryptographic-level context boundaries between clients, workspaces, and projects.
- Query embeddings, conversational memories, and agent context cards are scoped strictly to the active `project_id`.
- Scope guard intercepts every LLM prompt to prevent cross-project information leakage.

### 2. Dual-Tier Vector Memory Storage
- **Tier 1 (Embedded Desktop)**: Local ChromaDB instance with fast offline `SentenceTransformer("all-MiniLM-L6-v2")` embeddings (384 dimensions). Zero external database setup required.
- **Tier 2 (Enterprise pgvector)**: Scalable Supabase PostgreSQL pgvector pipeline featuring:
  - Canonical pillar classification (`deen`, `nafs_aql`, `maal`, `nasl_khalq`).
  - Dynamic chunking (250 words, 15% semantic overlap).
  - Multi-hop **Temporal Fusion Retriever** for cross-referencing timeline events and knowledge nodes.

### 3. Command Center & Cognitive Workload Management
- **Workload Analyzer**: Evaluates task complexity, cognitive load, and estimated execution hours.
- **Daily Planner & Prioritizer**: Automatically schedules daily agendas using an urgency-importance priority matrix.
- **Ghost Detector**: Monitors project telemetry to identify stalled or abandoned work streams before deadlines are breached.

### 4. Tri-Modal User Interfaces
- **God-Control Textual TUI (`main.py`)**: Terminal interface with real-time sidebar switching, active context inspector, and architectural canvas.
- **PyQt5 Desktop Application (`ui/desktop_app.py`)**: Dedicated multi-panel desktop workstation with project tree and visual feedback controls.
- **Streamlit Web Dashboard (`gui.py`)**: Browser-accessible rapid chat and automation console.

### 5. Native Security & DLP Hardening
- Complete environment variable isolation (`OPENROUTER_API_KEY`, `SHALI_MASTER_PIN`).
- Master PIN protection for revealing sensitive memories.
- Automated secret and credential regex filtering (`SECRET_PATTERNS`) before vector embedding.

---

## Quick Start

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Optional: Docker (for Langflow + Supabase orchestration)

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/inshalstratrum/Memory-Operating-System.git
cd Memory-Operating-System

# Install Python requirements
pip install -r requirements.txt
```

### 3. Environment Variables
Create a local `.env` file or export environment variables:

```powershell
$env:OPENROUTER_API_KEY = "your-openrouter-key"
$env:SHALI_MASTER_PIN   = "0000"
$env:EMBEDDING_MODEL    = "all-MiniLM-L6-v2"

# Optional: Supabase pgvector connection
$env:LIFEOS_POSTGRES_DSN = "postgresql://postgres:password@localhost:5432/postgres"
```

### 4. Launching the Interfaces

#### Launch Textual TUI (Terminal God-Control)
```powershell
python main.py
# Or use portable launcher:
.\run.bat
```

**TUI Keyboard Shortcuts**:
- `Ctrl + P`: Toggle Project Sidebar
- `Ctrl + C`: Focus Chat Panel
- `Ctrl + X`: Open Context Viewer
- `Ctrl + G`: Toggle Architecture Canvas
- `Ctrl + D`: Open Control Panel
- `Ctrl + Q`: Quit Application

#### Launch PyQt5 Desktop Studio
```powershell
python -m ui.desktop_app
```

#### Launch Streamlit Web Console
```powershell
streamlit run gui.py
```

---

## Directory Layout

```
Memory-Operating-System/
├── main.py                     # Primary Bootloader & Textual TUI entry point
├── config.py                   # Central environment & security configuration
├── docker-compose.yml          # Container configuration for Langflow & Supabase
├── requirements.txt            # Python dependencies
├── core/
│   ├── memory.py               # ChromaDB embedding & retrieval engine
│   ├── orchestrator.py         # Multi-agent input router and dispatcher
│   └── agents.py               # Persona definitions and prompt engineers
├── command_center/
│   ├── planner.py              # Execution planning
│   ├── analyzer.py             # Workload complexity analysis
│   ├── ghost_detector.py       # Inactivity & ghosting risk monitoring
│   └── prioritizer.py          # Urgency/importance ranker
├── project_isolation/
│   ├── manager.py              # Project and workspace metadata store
│   └── scope_guard.py          # Zero-bleed security boundaries
├── task_engine/
│   ├── tracker.py              # Task lifecycle & state transitions
│   ├── scheduler.py            # Event scheduling
│   └── notifier.py             # Notification dispatches
├── ui/
│   ├── app.py                  # Textual application layout
│   ├── shali.tcss              # Terminal CSS styling
│   ├── desktop_app.py          # PyQt5 native desktop interface
│   └── components/             # Reusable UI widgets
├── pgvector_pipeline/          # Scalable PostgreSQL pgvector backend
│   ├── src/lifeos_memory/      # Semantic chunking, DB connector & embeddings
│   ├── langflow_components/    # Temporal fusion retriever & execution governor
│   ├── sql/                    # pgvector schema definitions
│   └── seed/                   # Canonical architectural seeds
└── data/                       # Local data directory (templates included)
    ├── projects.example.json
    ├── tasks.example.json
    └── workspaces.example.json
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.