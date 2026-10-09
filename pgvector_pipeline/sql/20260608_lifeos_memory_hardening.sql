-- LifeOS memory hardening and provenance migration.
-- Canonical embedding contract: sentence-transformers/all-MiniLM-L6-v2, vector(384).

create extension if not exists vector;
create extension if not exists pgcrypto;
create extension if not exists "uuid-ossp";

do $$ begin
  create type pillar_code as enum ('deen', 'nafs_aql', 'maal', 'nasl_khalq');
exception when duplicate_object then null; end $$;

do $$ begin
  create type memory_type as enum (
    'short_term', 'long_term', 'task', 'persona', 'semantic', 'episodic', 'agent', 'archive'
  );
exception when duplicate_object then null; end $$;

do $$ begin
  create type lifeos_temporal_state as enum ('active_memory', 'historical', 'deprecated');
exception when duplicate_object then null; end $$;

do $$ begin
  create type lifeos_sensitivity as enum ('public', 'internal', 'sensitive', 'secret');
exception when duplicate_object then null; end $$;

do $$ begin
  create type lifeos_consent_level as enum (
    'suggestion', 'draft', 'low_risk_autopilot', 'explicit_approval'
  );
exception when duplicate_object then null; end $$;

create table if not exists public.life_memory_sources (
  id uuid primary key default gen_random_uuid(),
  source_uri text not null unique,
  source_title text,
  source_kind text not null default 'markdown',
  default_pillar pillar_code,
  content_sha256 text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.life_memory_ingestion_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  status text not null default 'running'
    check (status in ('running', 'completed', 'failed')),
  embedding_model text not null default 'sentence-transformers/all-MiniLM-L6-v2',
  embedding_dimensions integer not null default 384 check (embedding_dimensions = 384),
  source_count integer not null default 0 check (source_count >= 0),
  chunk_count integer not null default 0 check (chunk_count >= 0),
  metadata jsonb not null default '{}'::jsonb,
  error text
);

create table if not exists public.life_memory_chunks (
  id uuid primary key default gen_random_uuid(),
  pillar pillar_code not null,
  memory_kind memory_type not null,
  collection_name varchar(255) not null,
  content text not null,
  embedding vector(384),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  last_accessed_at timestamptz
);

alter table public.life_memory_chunks
  add column if not exists source_id uuid references public.life_memory_sources(id) on delete set null,
  add column if not exists ingestion_run_id uuid references public.life_memory_ingestion_runs(id) on delete set null,
  add column if not exists chunk_index integer not null default 0 check (chunk_index >= 0),
  add column if not exists content_sha256 text,
  add column if not exists temporal_state lifeos_temporal_state not null default 'active_memory',
  add column if not exists confidence_score numeric(4,3) not null default 0.500
    check (confidence_score >= 0 and confidence_score <= 1),
  add column if not exists sensitivity lifeos_sensitivity not null default 'internal',
  add column if not exists consent_level lifeos_consent_level not null default 'suggestion',
  add column if not exists embedding_model text not null default 'sentence-transformers/all-MiniLM-L6-v2',
  add column if not exists embedding_dimensions integer not null default 384 check (embedding_dimensions = 384),
  add column if not exists sanitization_applied boolean not null default false;

update public.life_memory_chunks
set content_sha256 = encode(extensions.digest(content, 'sha256'), 'hex')
where content_sha256 is null;

alter table public.life_memory_chunks
  alter column content_sha256 set not null;

create unique index if not exists idx_life_memory_chunks_unique_content
  on public.life_memory_chunks(collection_name, content_sha256);

create index if not exists idx_life_memory_chunks_hnsw
  on public.life_memory_chunks
  using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

create index if not exists idx_memory_pillar on public.life_memory_chunks(pillar);
create index if not exists idx_memory_collection on public.life_memory_chunks(collection_name);
create index if not exists idx_memory_temporal_state on public.life_memory_chunks(temporal_state);
create index if not exists idx_memory_source_id on public.life_memory_chunks(source_id);

create table if not exists public.life_audit_log (
  id bigserial primary key,
  event_type text not null,
  consent_level lifeos_consent_level not null default 'suggestion',
  protocol_flags text[] not null default array[]::text[],
  actor text not null default 'lifeos',
  source text,
  payload jsonb not null default '{}'::jsonb,
  payload_hash text not null,
  created_at timestamptz not null default now()
);

create or replace function public.lifeos_set_payload_hash()
returns trigger
language plpgsql
as $$
begin
  new.payload_hash := encode(extensions.digest(coalesce(new.payload::text, '{}'), 'sha256'), 'hex');
  return new;
end;
$$;

drop trigger if exists trg_life_audit_log_hash on public.life_audit_log;
create trigger trg_life_audit_log_hash
before insert on public.life_audit_log
for each row execute function public.lifeos_set_payload_hash();

create or replace function public.lifeos_reject_audit_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'life_audit_log is append-only';
end;
$$;

drop trigger if exists trg_life_audit_log_no_update on public.life_audit_log;
create trigger trg_life_audit_log_no_update
before update on public.life_audit_log
for each row execute function public.lifeos_reject_audit_mutation();

drop trigger if exists trg_life_audit_log_no_delete on public.life_audit_log;
create trigger trg_life_audit_log_no_delete
before delete on public.life_audit_log
for each row execute function public.lifeos_reject_audit_mutation();

drop function if exists public.match_life_memories(vector, double precision, integer);

create or replace function public.match_life_memories (
  query_embedding vector(384),
  match_threshold double precision default 0.20,
  match_count integer default 8,
  filter_pillar pillar_code default null,
  filter_collections text[] default null,
  include_general boolean default true,
  include_sensitive boolean default false
)
returns table (
  id uuid,
  pillar pillar_code,
  memory_kind memory_type,
  collection_name varchar,
  content text,
  metadata jsonb,
  temporal_state lifeos_temporal_state,
  confidence_score numeric,
  sensitivity lifeos_sensitivity,
  source_uri text,
  similarity double precision,
  final_score double precision
)
language sql
stable
security definer
set search_path = public
as $$
  with scored as (
    select
      c.id,
      c.pillar,
      c.memory_kind,
      c.collection_name,
      c.content,
      c.metadata,
      c.temporal_state,
      c.confidence_score,
      c.sensitivity,
      s.source_uri,
      1 - (c.embedding <=> query_embedding) as similarity,
      (
        (1 - (c.embedding <=> query_embedding))
        + (c.confidence_score::double precision * 0.10)
        + case c.temporal_state
            when 'active_memory' then 0.050
            when 'historical' then 0.000
            else -1.000
          end
        - least(extract(epoch from (now() - c.created_at)) / 86400.0 * 0.0002, 0.20)
      ) as final_score
    from public.life_memory_chunks c
    left join public.life_memory_sources s on s.id = c.source_id
    where c.embedding is not null
      and c.temporal_state <> 'deprecated'
      and (filter_pillar is null or c.pillar = filter_pillar)
      and (
        filter_collections is null
        or c.collection_name = any(filter_collections)
        or (include_general and c.collection_name in ('lifeos_core', 'general', 'shali_core'))
      )
      and (include_sensitive or c.sensitivity not in ('sensitive', 'secret'))
  )
  select *
  from scored
  where similarity > match_threshold
  order by final_score desc, similarity desc
  limit greatest(match_count, 0);
$$;

create or replace function public.lifeos_insert_memory_chunk (
  p_pillar pillar_code,
  p_memory_kind memory_type,
  p_collection_name varchar,
  p_content text,
  p_embedding vector(384),
  p_metadata jsonb default '{}'::jsonb,
  p_source_id uuid default null,
  p_ingestion_run_id uuid default null,
  p_chunk_index integer default 0,
  p_temporal_state lifeos_temporal_state default 'active_memory',
  p_confidence_score numeric default 0.500,
  p_sensitivity lifeos_sensitivity default 'internal',
  p_consent_level lifeos_consent_level default 'suggestion',
  p_sanitization_applied boolean default false
)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_id uuid;
  v_hash text := encode(extensions.digest(p_content, 'sha256'), 'hex');
begin
  insert into public.life_memory_chunks (
    pillar,
    memory_kind,
    collection_name,
    content,
    embedding,
    metadata,
    source_id,
    ingestion_run_id,
    chunk_index,
    content_sha256,
    temporal_state,
    confidence_score,
    sensitivity,
    consent_level,
    sanitization_applied
  )
  values (
    p_pillar,
    p_memory_kind,
    p_collection_name,
    p_content,
    p_embedding,
    coalesce(p_metadata, '{}'::jsonb),
    p_source_id,
    p_ingestion_run_id,
    greatest(p_chunk_index, 0),
    v_hash,
    p_temporal_state,
    least(greatest(p_confidence_score, 0), 1),
    p_sensitivity,
    p_consent_level,
    p_sanitization_applied
  )
  on conflict (collection_name, content_sha256)
  do update set
    pillar = excluded.pillar,
    memory_kind = excluded.memory_kind,
    embedding = excluded.embedding,
    metadata = excluded.metadata,
    source_id = excluded.source_id,
    ingestion_run_id = excluded.ingestion_run_id,
    chunk_index = excluded.chunk_index,
    temporal_state = excluded.temporal_state,
    confidence_score = excluded.confidence_score,
    sensitivity = excluded.sensitivity,
    consent_level = excluded.consent_level,
    embedding_model = 'sentence-transformers/all-MiniLM-L6-v2',
    embedding_dimensions = 384,
    sanitization_applied = excluded.sanitization_applied
  returning id into v_id;

  insert into public.life_audit_log (
    event_type,
    consent_level,
    protocol_flags,
    actor,
    source,
    payload
  )
  values (
    'memory.upsert',
    p_consent_level,
    case
      when p_sensitivity in ('sensitive', 'secret') then array['sensitive_memory']
      else array[]::text[]
    end,
    'lifeos_memory_pipeline',
    p_collection_name,
    jsonb_build_object(
      'memory_id', v_id,
      'pillar', p_pillar,
      'memory_kind', p_memory_kind,
      'source_id', p_source_id,
      'ingestion_run_id', p_ingestion_run_id,
      'content_sha256', v_hash,
      'sanitization_applied', p_sanitization_applied
    )
  );

  return v_id;
end;
$$;

alter table public.life_memory_chunks enable row level security;
alter table public.life_memory_sources enable row level security;
alter table public.life_memory_ingestion_runs enable row level security;
alter table public.life_audit_log enable row level security;

drop policy if exists "LifeOS_Sovereign_Admin_Only" on public.life_memory_chunks;
drop policy if exists life_memory_chunks_service_only on public.life_memory_chunks;
drop policy if exists life_memory_sources_service_only on public.life_memory_sources;
drop policy if exists life_memory_ingestion_runs_service_only on public.life_memory_ingestion_runs;
drop policy if exists life_audit_log_service_only on public.life_audit_log;

create policy life_memory_chunks_service_only
  on public.life_memory_chunks
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create policy life_memory_sources_service_only
  on public.life_memory_sources
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create policy life_memory_ingestion_runs_service_only
  on public.life_memory_ingestion_runs
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');

create policy life_audit_log_service_only
  on public.life_audit_log
  for insert
  with check (auth.role() = 'service_role');

revoke all on table public.life_memory_chunks from public, anon, authenticated, service_role;
revoke all on table public.life_memory_sources from public, anon, authenticated, service_role;
revoke all on table public.life_memory_ingestion_runs from public, anon, authenticated, service_role;
revoke all on table public.life_audit_log from public, anon, authenticated, service_role;
revoke all on all functions in schema public from public, anon, authenticated;

grant select, insert, update on table public.life_memory_chunks to service_role;
grant select, insert, update on table public.life_memory_sources to service_role;
grant select, insert, update on table public.life_memory_ingestion_runs to service_role;
grant select, insert on table public.life_audit_log to service_role;
grant usage, select on sequence public.life_audit_log_id_seq to service_role;
grant execute on function public.match_life_memories(
  vector(384), double precision, integer, pillar_code, text[], boolean, boolean
) to service_role;
grant execute on function public.lifeos_insert_memory_chunk(
  pillar_code, memory_type, varchar, text, vector(384), jsonb, uuid, uuid, integer,
  lifeos_temporal_state, numeric, lifeos_sensitivity, lifeos_consent_level, boolean
) to service_role;
