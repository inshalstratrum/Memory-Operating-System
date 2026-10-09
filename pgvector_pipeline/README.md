# LifeOS Memory Pipeline

Local-first Supabase pgvector memory for Shali LifeOS.

## Active Contracts

- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
- Vector dimensions: `384`
- Primary store: local Supabase Postgres + pgvector
- Canonical pillars: `deen`, `nafs_aql`, `maal`, `nasl_khalq`
- Default chunking: 250 words with 15% overlap

## Environment

Set one database connection string before running the scripts:

```powershell
$env:LIFEOS_POSTGRES_DSN="postgresql://postgres:<password>@localhost:5432/postgres"
```

Inside Docker, after Langflow is attached to the `supabase_default` network, use:

```text
postgresql://postgres:<password>@db:5432/postgres
```

The scripts intentionally do not store Supabase service keys or database passwords.

## Commands

```powershell
python -m lifeos_memory.scripts.ingest_markdown --source "D:\LifeOS\Memory" --collection lifeos_core
python -m lifeos_memory.scripts.search_memory "What is the LifeOS pillar architecture?"
```

For the current workstation, prefer running from an environment with `sentence-transformers`
and `psycopg` installed. The Langflow container already has those libraries.
