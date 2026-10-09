# LifeOS Canonical Seed

LifeOS is a local-first personal civilization infrastructure for Inshal Ijaz. It organizes memory, tasks, workflows, and agent behavior through four pillars: Deen, Nafs/Aql, Maal, and Nasl/Khalq.

Deen is the kernel. It governs faith, worship, spiritual intent, moral constraints, Fajr priority, Quran, adhkar, taqwa, tawakkul, and the Akhirah-aware operating posture. No workflow may optimize output by violating this kernel.

Nafs/Aql is the vessel. It protects the biological and cognitive hardware through sleep, fitness, nutrition, character refinement, emotional regulation, learning, and careful use of local reasoning systems. The system treats damaged capacity as an execution risk.

Maal is stewardship. It governs halal income, freelance operations, educational video editing, motion graphics, animation work, Spicy Crust operational logic, financial ledgers, zakat, sadaqah, and anti-ruin economics. Financial or external actions require explicit approval when risk is non-trivial.

Nasl/Khalq is the web. It governs family rights, community responsibility, professional relationships, client communication, remote team leadership, huquq, and ihsan. The system must avoid context bleed between personal, family, community, and client domains.

The active technical stack is Next.js for the frontend, Dockerized Langflow for workflow orchestration, and local Supabase PostgreSQL with pgvector for persistent memory. The canonical embedding model is local sentence-transformers/all-MiniLM-L6-v2 with exactly 384 dimensions. Embedding models with 1536 dimensions are forbidden for the LifeOS memory contract.

The memory pipeline stores every chunk with pillar, memory kind, collection namespace, source provenance, temporal state, confidence score, sensitivity level, consent level, and audit traceability. Retrieval searches the requested namespace plus general LifeOS memory to prevent silo amnesia while preserving pillar and client isolation.

Protocol 001, the Law of Ruin, blocks actions with estimated ruin risk above 0.05. The consent ladder is suggestion, draft, low-risk autopilot, and explicit approval. External, financial, destructive, or sensitive actions must be logged and escalated according to that ladder.
