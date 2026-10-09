from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .contracts import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, MemoryChunk
from .embeddings import vector_literal


def get_dsn(explicit_dsn: str | None = None) -> str:
    dsn = explicit_dsn or os.getenv("LIFEOS_POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("Set LIFEOS_POSTGRES_DSN before using the memory pipeline")
    return dsn


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LifeOSMemoryStore:
    def __init__(self, dsn: str | None = None):
        self.dsn = get_dsn(dsn)

    def connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def start_run(self, metadata: dict[str, Any] | None = None) -> str:
        with self.connect() as conn:
            row = conn.execute(
                """
                insert into public.life_memory_ingestion_runs (metadata)
                values (%s::jsonb)
                returning id
                """,
                (json.dumps(metadata or {}),),
            ).fetchone()
            return str(row["id"])

    def finish_run(
        self,
        run_id: str,
        status: str,
        source_count: int,
        chunk_count: int,
        error: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                update public.life_memory_ingestion_runs
                set completed_at = now(),
                    status = %s,
                    source_count = %s,
                    chunk_count = %s,
                    error = %s
                where id = %s
                """,
                (status, source_count, chunk_count, error, run_id),
            )

    def upsert_source(
        self,
        source_path: Path,
        title: str,
        content: str,
        default_pillar: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        with self.connect() as conn:
            row = conn.execute(
                """
                insert into public.life_memory_sources (
                  source_uri,
                  source_title,
                  source_kind,
                  default_pillar,
                  content_sha256,
                  metadata
                )
                values (%s, %s, 'markdown', %s, %s, %s::jsonb)
                on conflict (source_uri) do update set
                  source_title = excluded.source_title,
                  default_pillar = excluded.default_pillar,
                  content_sha256 = excluded.content_sha256,
                  metadata = excluded.metadata
                returning id
                """,
                (
                    str(source_path),
                    title,
                    default_pillar,
                    sha256_text(content),
                    json.dumps(metadata or {}),
                ),
            ).fetchone()
            return str(row["id"])

    def upsert_chunks(
        self,
        chunks: Iterable[MemoryChunk],
        embeddings: Iterable[list[float]],
        source_ids: dict[Path, str],
        run_id: str,
    ) -> int:
        count = 0
        with self.connect() as conn:
            with conn.cursor() as cur:
                for chunk, embedding in zip(chunks, embeddings, strict=True):
                    chunk.validate()
                    cur.execute(
                        """
                        select public.lifeos_insert_memory_chunk(
                          %s::pillar_code,
                          %s::memory_type,
                          %s::varchar,
                          %s,
                          %s::vector(384),
                          %s::jsonb,
                          %s::uuid,
                          %s::uuid,
                          %s,
                          %s::lifeos_temporal_state,
                          %s::numeric,
                          %s::lifeos_sensitivity,
                          %s::lifeos_consent_level,
                          %s
                        )
                        """,
                        (
                            chunk.pillar,
                            chunk.memory_kind,
                            chunk.collection_name,
                            chunk.content,
                            vector_literal(embedding),
                            json.dumps(chunk.metadata),
                            source_ids[chunk.source_path],
                            run_id,
                            chunk.chunk_index,
                            chunk.temporal_state,
                            chunk.confidence_score,
                            chunk.sensitivity,
                            chunk.consent_level,
                            chunk.sanitization_applied,
                        ),
                    )
                    count += 1
        return count

    def search(
        self,
        query_embedding: list[float],
        match_threshold: float = 0.2,
        match_count: int = 8,
        pillar: str | None = None,
        collections: list[str] | None = None,
        include_sensitive: bool = False,
    ) -> list[dict[str, Any]]:
        if len(query_embedding) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"Expected {EMBEDDING_DIMENSIONS}-dimensional query embedding")
        with self.connect() as conn:
            rows = conn.execute(
                """
                select *
                from public.match_life_memories(
                  %s::vector(384),
                  %s::double precision,
                  %s::integer,
                  %s::pillar_code,
                  %s::text[],
                  true,
                  %s::boolean
                )
                """,
                (
                    vector_literal(query_embedding),
                    match_threshold,
                    match_count,
                    pillar,
                    collections,
                    include_sensitive,
                ),
            ).fetchall()
            return [dict(row) for row in rows]


def runtime_contract() -> dict[str, Any]:
    return {
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
    }
