# DBoT Target Architecture: GitHub Repo as Source of Truth

**Date**: 2026-07-11
**Status**: Proposed (Phases 1–3 resolved, legacy Supabase repo cleanup shipped ahead of Phase 6 — see Migration phases below)
**Supersedes**: `docs/rearchitecture-plan.md` (2026-05-29) — see that file's banner.

## Summary

Database of Things (DBoT) stops being a Postgres database that curators write to
directly. It becomes **this public GitHub repo**: canonical collectibles data lives
as files, curators (human or AI) propose changes as pull requests, and each
collection carries its own `AGENTS.md` (curation hints) and item property template
right next to its data. DBoT itself stays deliberately dumb — a plain, public,
transparent git repo with a CI job that checks data quality. It has no database,
no secrets, and no knowledge that Will's Attic or Supabase exist. Anyone could
clone it and use it for something else entirely.

Separately, the Supabase project that currently hosts DBoT's Postgres gets
**repurposed** as Will's Attic's own application database. It stops being "the
database curators write to" and becomes "the database attic-api reads and writes
directly" — holding both user data (currently on a separate Railway Postgres) and a
synced, read-only mirror of this repo's canonical data. **Will's Attic owns the
sync**: attic-api is the platform that needs to be performant, so it's the one that
pulls from DBoT on its own schedule, at its own tolerance for staleness. DBoT never
pushes anywhere and never holds credentials to anything of Will's Attic's.

## Why

- **Curation as code review.** A PR is a natural place for a diff, a discussion, and
  an approval — better than a curator (AI or human) writing straight to a database
  with no review gate. It also lets outside contributors propose changes without
  ever getting write access to production infrastructure.
- **Guidance travels with the data.** A per-collection `AGENTS.md` and item template
  live in the same directory as the entities they govern — discoverable by anyone
  (or any agent) opening that folder, versioned alongside the data it describes,
  instead of living in a separate prompt/config system that can drift out of sync.
- **One database, not three moving parts.** Today attic-api's own data lives in a
  Railway Postgres, canonical data lives in a separate Supabase Postgres, and every
  canonical read is a network hop through a GraphQL API in between. Consolidating
  onto one Postgres (Supabase, repurposed) removes a service boundary and a
  network hop for no loss of correctness — the *real* source of truth for canonical
  data is moving to git, so the database was never the durable record anyway; it's
  just a cache.

## The model

### Two roles, two stores

| Store | Role | Written by |
|---|---|---|
| `database-of-things` (this GitHub repo) | Source of truth for canonical collectibles data | Curator PRs (human or AI), reviewed and merged |
| Supabase Postgres (repurposed) | Will's Attic's application database | (a) attic-api directly, for user data. (b) attic-api's own sync command, for the canonical-data mirror — never edited by hand, never by anything in DBoT |

attic-api connects to the Supabase Postgres directly for **everything** — its own
user tables and the canonical-data mirror both live there. The mirror is rebuilt
from git; if it's ever wrong, the fix is a PR to this repo, not a manual DB edit.

**No submodule.** Pinning "which DBoT commit is our cache built from" doesn't need
a git submodule (extra clone/init steps, easy to silently drift). attic-api stores
the last-synced commit SHA itself, as one row of sync state, and uses GitHub's
compare API to fetch exactly what changed since then.

### Repo layout

Collections are directories. Each carries curation guidance and a schema; each
leaf item is one file.

```
collections/
  pokemon-tcg/
    AGENTS.md                 # curation hints for this whole category
    template.schema.json      # JSON Schema for item `attributes`
    _collection.yaml          # this collection's own entity record
    base-set/
      _collection.yaml        # nested collection, inherits AGENTS.md + template
      charizard-4-102.yaml
      blastoise-2-102.yaml
      venusaur-15-102.yaml
    jungle/
      _collection.yaml
      ...
  amiibo/
    AGENTS.md
    template.schema.json
    _collection.yaml
    mario.yaml
    ...
```

A nested directory only needs its own `AGENTS.md`/`template.schema.json` if its
conventions differ from its parent's — otherwise it inherits from the nearest
ancestor that has one. `_collection.yaml` is required at every level (it's the
entity record for the collection/set itself, same shape as any other entity plus
`type: collection`).

### Entity file format

One YAML file per entity. Human-readable, diffable, comments allowed for curator
notes on individual items.

```yaml
id: 3f4334f3-6a41-45fb-a1c1-dcf44566491e   # stable, generated once, never reused
name: Charizard
type: card
number: "4/102"
rarity: Holo Rare
year: 1999
attributes:
  hp: 120
  stage: Stage 2
  card_type: Fire
image:
  source_url: https://images.pokemontcg.io/base1/4_hires.png
```

`attributes` is validated against the collection's `template.schema.json`; the
top-level fields (`id`, `name`, `type`) are structural and validated the same way
everywhere.

**No `collection:`/`parent_collection:` field.** Parent membership is *derived
from directory position*, not a hand-typed reference — this file lives in
`base-set/`, so its parent is whatever `base-set/_collection.yaml` says it is.
A slug string duplicating that would be a second place for the same fact to go
stale (rename the directory, forget to bulk-update every child's reference).
Directory position can't drift from itself.

### Curation workflow

1. A curator (human, or an AI agent running a skill) branches, edits or adds entity
   files, updates `AGENTS.md`/template if the collection's conventions changed.
2. Opens a PR. CI runs the validator (schema conformance, UUID uniqueness/format,
   required files present).
3. Review — human, and/or an AI review pass (a natural evolution of the existing
   `curator-audit-*` skills in the `wills-attic` repo, pointed at a diff instead of
   a live query).
4. Merge to `main`.
5. On its own schedule, attic-api's sync command checks whether `main` has moved
   since the last sync, and if so pulls and upserts the changed entities into the
   Supabase mirror, keyed on `id`. Because git is the source of truth, the mirror
   can always be thrown away and rebuilt from a full repo scan — it's a cache, not
   a record. DBoT does nothing here; there is no push, no webhook, no CI step
   reaching out to Will's Attic. attic-api reaches in, on its own terms, and can
   tolerate being a sync interval behind.

### Sync mechanism (attic-api side)

- **State**: one row (or table) in attic-api's database — `dbot_sync_state`, holding
  `last_synced_sha` and `last_synced_at`. Nothing about the mirror's freshness lives
  in DBoT.
- **Trigger**: a scheduled Artisan command (e.g. `php artisan dbot:sync`), run on
  Laravel's scheduler at whatever interval matches the "slightly stale is fine"
  tolerance (minutes-to-hours, not real-time).
- **Check**: fetch DBoT's current `main` SHA (`GET /repos/.../commits/main`, cheap,
  public, no auth required for a public repo). If it matches `last_synced_sha`,
  stop — nothing to do.
- **Diff**: if it's the first run, walk the full `collections/**` tree. Otherwise
  call GitHub's compare API (`GET /repos/.../compare/{last_synced_sha}...{new_sha}`)
  to get exactly the files that changed, added, or were removed since last time —
  no full-repo rescan needed on steady-state syncs.
- **Apply**: for each changed/added entity file, fetch its content, parse the YAML,
  upsert into the mirror keyed on `id`; for each removed file, delete the
  corresponding mirror row. Re-validating against `template.schema.json` here is
  optional-but-cheap insurance (DBoT's own CI already validated it pre-merge).
- **Commit**: update `dbot_sync_state.last_synced_sha` to the new SHA once the sync
  completes successfully.

### Images (open question)

Flagged as a real challenge, not yet solved:

- Binary images should **not** live in the git repo — it bloats history, makes PR
  diffs noisy, and Git LFS has its own cost/complexity. An entity file should
  reference an image (`source_url`, or a stable key), not embed it.
- The current system already has a working image pipeline — Supabase Storage with
  originals + generated thumbnails. That can very likely keep serving this purpose
  as "where image bytes live," decoupled from where the *metadata* about which
  image belongs to which entity lives (that part moves to git, like everything
  else).
- Open questions to resolve before Phase 2: who fetches a `source_url` into Storage
  the first time (the sync job, or a separate step?), how re-localization/thumbnail
  regeneration is triggered when an entity's image reference changes in a PR, and
  what happens to the ~existing images already in Storage for currently-live
  collections during migration.

### What changes for attic-api / the "never write to DBoT" rule

The rule doesn't go away, it just stops being enforced by a network boundary:

- **"Never write to DBoT" now means "never write to the canonical-mirror tables in
  Supabase directly."** The only legitimate writer of those tables is attic-api's
  own sync command. The only way to change canonical data is a PR to this repo.
- Because the sync command and the rest of attic-api share both a Postgres
  instance *and* a codebase, this is no longer a network/service boundary — it's a
  convention enforced by code review: application code reads the mirror tables,
  only `dbot:sync` (and its migrations) writes them.
- **Keep no FK constraints** from `user_items`/`wishlists`/`user_collection_favorites`
  to the mirror tables, even though they're now in the same database. The mirror
  can be dropped and rebuilt from git at any time; a hard FK would turn that into a
  breaking migration instead of a no-op.

## Migration phases

- **Phase 0** — this doc.
- **Phase 1 (now)** — scaffold this repo's new file-based layout (`collections/`),
  build the validator + CI wiring, build the curator-facing tooling to add/edit
  entries in the new format. Purely additive: the existing Supabase-backed system
  keeps running untouched, nothing in production changes.
- **Phase 2 (shipped)** — in `wills-attic`/`attic-api`: `dbot_entities` and
  `dbot_sync_state` tables plus the `dbot:sync` command described above.
  **Correction from the original plan below**: these tables were added as ordinary
  Laravel migrations, which means they live in attic-api's *existing* Postgres
  (the separate Railway instance, alongside `users`/`user_items`/etc.) rather than
  in Supabase directly. Standing up a second live DB connection to Supabase for
  just this table, only to fold it into the same connection again a phase later
  in Phase 4, was extra transitional complexity for no lasting benefit — the
  mirror is co-located with attic-api's app data now, and both move to Supabase
  together in one cutover instead of two. Nothing in `database-of-things` changed
  for this phase.
- **Phase 3 (resolved)** — migrate real, already-verified collections into the
  new format and prove the sync end-to-end against production for parity. Base
  Set Pokémon (102/102 cards) shipped as the proof of concept. Scoping the rest
  found production data for the other five legacy curator collections is mostly
  empty or low-quality (American Comics, LEGO Sets, Bluey Figures, NTSC Video
  Games have next to nothing real; Pokémon TCG has ~380 more sets but with
  duplicate/inconsistent collection records) — not worth migrating forward.
  **Decision: discard it.** `collections/` stays at just Base Set for now; the
  rest gets rebuilt properly through PR-based curation (human and AI) over time,
  rather than carrying forward messy legacy data. This also means the old
  Supabase schema/data no longer needs preserving *at all* — see below.
- **Phase 4** — migrate attic-api's *entire* database — its own app tables
  (`users`, `user_items`, `wishlists`, `user_collection_favorites`, `api_tokens`,
  plus `dbot_entities`/`dbot_sync_state` from Phase 2) — from the separate Railway
  Postgres into the Supabase project in one move. Point attic-api's DB connection
  at it. Independent of Phase 5 below — this consolidates *where* attic-api's own
  database lives, not what it reads for canonical data.
- **Phase 5** — cut over attic-api's canonical-data reads from
  `DatabaseOfThingsService` (GraphQL-over-HTTP) to direct SQL against the mirror
  tables. This is the real gate on removing Supabase from `database-of-things` —
  until it's done, Supabase has to stay up and correctly schema'd. Requires more
  than copying data over; `DatabaseOfThingsService` does things the mirror can't
  serve yet:
  - **Search** — needs an actual index over the mirror (pg_trgm or full-text at
    minimum); the mirror today has no index beyond its primary key.
  - **Semantic search — open decision, not just engineering.** Its embedding
    generation lived in `services/embedding-worker`, already deleted from this
    repo. Does attic-api build its own embedding pipeline (text, and/or reuse the
    `clip-service` image-embedding pattern it already has), or is semantic search
    dropped/simplified (e.g. to plain text search) as part of this migration?
  - **Hierarchy** — `collection_path` as a flat string on `dbot_entities` likely
    can't replace what `relationships`/parent-child traversal, item-parents
    lookup, and collection filter fields do today. Probably needs an explicit
    `parent_id` or relationships shape added to the mirror schema.
  - **Representative images** (BFS descendant-image lookup) — needs an equivalent
    query path against the mirror's hierarchy once that exists.
- **Phase 6** — decommission the *live* Supabase project (the actual running
  database and its GraphQL surface) and the separate Railway app-Postgres.
  Finalize the images answer. Still gated on Phase 5 — attic-api reads that
  live instance directly over HTTPS today, so it has to stay up and correctly
  populated until nothing depends on it anymore.

  **Note**: this repo's own copy of the schema — `supabase/migrations/`,
  `supabase/config.toml`, `bin/` (the local Supabase CLI), `tests/`, the
  `db-tests` CI job, `services/embedding-worker/`, and the historical
  planning docs describing that system — has *already been removed*, ahead of
  Phase 5, once the Phase 3 discard decision above was made. Deleting those
  files never touched the live database (attic-api's reads are independent of
  what's version-controlled here); what they gave up was the ability to
  reproduce that schema from scratch, which nobody needs anymore since the
  data behind it isn't being carried forward. The MCP server's remaining read
  tools (research helpers for curators, querying the still-live instance) were
  a separate, independent decision from this cutover, now resolved: retired
  rather than repurposed, and removed from this repo. `collections/` is small
  enough to browse directly, and the legacy data those tools searched isn't
  being carried forward anyway (see Phase 3 above).

The standalone Agent-SDK curator service remains the long-term target for running
audits/updates at scale (see `wills-attic/docs/plans/2026-07-12-ai-curator-system-design.md`)
— it just changes what it does at the point of action: instead of calling MCP write
tools against Postgres, it opens a PR against this repo.

## Open questions

- Entity file format: YAML chosen for readability/diffability/comments; revisit if
  schema validation tooling or merge-conflict rates make a different format
  preferable.
- Full resolution of the images question above.
