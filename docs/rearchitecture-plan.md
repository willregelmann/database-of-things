# Rearchitecture Plan

Status: **proposed** · Authored: 2026-05-29

> **SUPERSEDED (2026-07-11).** This plan assumed Supabase stays as DBoT's own
> infrastructure and rebuilds the stack on top of it (Drizzle core, Hono REST API).
> That assumption no longer holds: DBoT's source of truth is moving to this GitHub
> repo (files + curator PRs, per-collection `AGENTS.md`/templates), and Supabase is
> being repurposed as Will's Attic's own application database instead — not DBoT's.
> See `docs/dbot-target-architecture.md` for the current plan. Kept here for the
> historical record — the schema-cleanup thinking below (unified `entities` table,
> `entity_external_ids`) may still be useful input for the synced-mirror schema.

A clean-room rearchitecture of the collectibles database. Undertaken now because
there is **no production data yet** — local data is seed-only — so the schema,
data model, and stack can be reshaped without a data migration.

## Goals

1. **Reconsider the data model** — move from a generic untyped graph + JSONB-for-
   everything toward a sharper model that distinguishes ownership from membership.
2. **Prep for scale** — async embeddings, hybrid search, reliable dedup, and a
   layered codebase where business logic is testable code, not SQL.
3. **Clean separation** — a shared core with MCP and a public API as thin adapters.

## Settled decisions

| # | Decision | Choice |
|---|----------|--------|
| Model | Variants & components | **Absorbed into `entities`** (no separate tables) |
| Model | Subordinate cascade | **FK column** `entities.parent_id ON DELETE CASCADE` (not trigger/core) |
| Model | Attribute schema | **JSONB, no registry/allowlist.** Descriptive `attribute_key_stats` matview + optional mechanical key-normalization. Formalize per-lineage later, if data warrants. |
| Model | External IDs | **Own table** `entity_external_ids(source, source_id)` with `UNIQUE(source, source_id)` for reliable dedup |
| Model | Edges | `relationships.kind ∈ {contains, member_of}` (M:N graph only; ownership moved to FK column) |
| Stack | Public API | **REST + OpenAPI** (Hono), with composite read endpoints. Not GraphQL — read-mostly catalog wants CDN/HTTP caching; GraphQL is a later adapter if needed. |
| Stack | Embeddings | **Self-hosted**, async via `embedding_jobs` + worker. Keep Transformers.js (TS) for now. |
| Stack | Host | **Stay on Supabase as infrastructure** (Postgres+pgvector + Storage), decoupled from its app features (auto-GraphQL/PostgREST/RLS-as-API). Swappable later via core abstraction. |
| Stack | Search | **Hybrid** — RRF over full-text + trigram + vector (replaces trigram-first hack) |

## Why the old model strained

- One generic untyped "contains" edge conflated canonical containment with mere
  membership (the `curators.collection_id` + separate `curator_collections` split
  was a symptom).
- Variants/components/entities were three copies of the same machinery → three
  near-identical `*_additional_images` tables.
- Dedup keyed on the "first JSONB external_id key" — non-deterministic, a latent bug.
- Embeddings generated synchronously in the write path.
- ~250 lines of business logic trapped in the `import_curator_batch` PL/pgSQL RPC.
- 52 migrations of churn (`image_url` added → keyed → re-pathed → moved to `images`).

## Target schema (shape)

- **`entities`** — unified. Adds `parent_id` / `parent_role ∈ {variant,component}` /
  `quantity` / `parent_order` (FK-cascade ownership), `attributes` JSONB,
  `name_embedding` (nullable, filled async), generated `search_vector`.
  Subordinates are `WHERE parent_id IS NULL` filtered out of top-level browse.
- **`entity_external_ids`** — `(source, source_id)` PK, `UNIQUE(source, source_id)`.
- **`relationships`** — `kind ∈ {contains, member_of}` only; `order`, `quantity`.
- **`images`** — unchanged (already clean): `image_url`, `thumbnail_url`,
  `embedding vector(512)`, HNSW index.
- **`entity_images`** — single additional-images join table (was three).
- **`embedding_jobs`** — outbox drained by the worker.
- **`attribute_key_stats`** — descriptive matview of attribute keys by
  category/parent. No enforcement.

Cascade integrity (subordinates die with their parent) is native FK behavior — no
trigger, no core logic. Containment is the genuine M:N graph; ownership is a tree.

## Architecture (shared core + thin adapters)

```
  MCP adapter      Public API (REST)      embedding-worker
      \                 |                      /
       \                |                     /
              ┌──────── @dot/core ────────┐
              │ domain + typed DAL        │  CRUD · dedup · import pipeline ·
              │ (Drizzle)                 │  hierarchy · hybrid search ·
              └─────────────┬─────────────┘  embedding enqueue · key normalize
              Postgres + pgvector   Object store (behind StorageProvider iface)
```

Business logic lives in `@dot/core`. The DB holds schema + constraints + indexes.
RLS becomes optional defense-in-depth (authz lives in core/API).

## Tooling defaults

- Monorepo: **pnpm workspaces** + TS project refs
- Query builder + migrations: **Drizzle**
- API framework: **Hono**
- Tests: **Vitest** + disposable Postgres

## Phases

Sequenced so the system keeps working throughout. Critical path: **0 → 1 → 2 → 4**
(curators working = "rearchitecture v1 done"). 3 and 5 parallelize after 2.
Cleanup (6) is last and irreversible, only after the new path is proven.

- **Phase 0 — Scaffold** the pnpm workspace (`packages/core`, `apps/mcp`,
  `apps/api`, `apps/embedding-worker`), Drizzle, Vitest, CI, `StorageProvider` stub.
  *Gate:* build + empty suite green.
- **Phase 1 — Clean schema baseline** in Drizzle; archive the 52 old migrations;
  schema/constraint tests. *Gate:* deleting a base entity provably cascades to its
  variants/components via FK.
- **Phase 2 — `@dot/core`** (most effort): entity CRUD, correct external-id dedup,
  import pipeline ported from the PL/pgSQL RPC to tested TS, hierarchy ops
  (recursive CTE), hybrid search (RRF), embedding enqueue, `attribute_key_stats`.
  *Gate:* import-then-search integration round trip green.
- **Phase 3 — Embedding worker**: drain `embedding_jobs`, Transformers.js, backfill
  seed rows. *Gate:* import → job → vector filled → semantic search hit.
- **Phase 4 — Re-point MCP onto core** (regression gate): 16 tools become thin
  wrappers; variant/component via `parent_id`, images via `entity_images`, bulk via
  `core.import`. *Gate:* a real curator (e.g. Pokemon TCG) runs end-to-end.
- **Phase 5 — Public REST API** (Hono over core): composite read endpoints,
  pagination, `Cache-Control`/ETag, OpenAPI. Read-only public; writes behind a
  service credential. *Gate:* browse-a-set-with-cards-and-images in one cacheable
  request.
- **Phase 6 — Cleanup & cutover**: drop vestigial DB objects (`curators`,
  `curator_operations`, `curator_runs`, `curator_collections`,
  `entity_type_registry`, `validate_card_*`, `entity_data_quality_issues`,
  `import_curator_batch`); delete `services/embedding-worker/` (Python),
  `docker-compose.embedding.yml`, and the stale top-level design docs; rewrite
  `CLAUDE.md` + `README.md`; re-seed and verify.
- **Phase 7 — Scale hardening** (deferred, when it hurts): closure table for
  hierarchy, RLS defense-in-depth, revisit Neon+R2 / managed embeddings.
