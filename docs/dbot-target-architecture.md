# DBoT Target Architecture: GitHub Repo as Source of Truth

**Date**: 2026-07-11
**Status**: Proposed (Phase 1 scaffolding in progress)
**Supersedes**: `docs/rearchitecture-plan.md` (2026-05-29) — see that file's banner.

## Summary

Database of Things (DBoT) stops being a Postgres database that curators write to
directly. It becomes **this public GitHub repo**: canonical collectibles data lives
as files, curators (human or AI) propose changes as pull requests, and each
collection carries its own `AGENTS.md` (curation hints) and item property template
right next to its data.

Separately, the Supabase project that currently hosts DBoT's Postgres gets
**repurposed** as Will's Attic's own application database. It stops being "the
database curators write to" and becomes "the database attic-api reads and writes
directly" — holding both user data (currently on a separate Railway Postgres) and a
synced, read-only mirror of this repo's canonical data. attic-api talks to it with a
normal DB connection, not an HTTP/GraphQL round trip to a different service.

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
| Supabase Postgres (repurposed) | Will's Attic's application database | (a) attic-api directly, for user data. (b) A sync job only, for the canonical-data mirror — never edited by hand, never by attic-api |

attic-api connects to the Supabase Postgres directly for **everything** — its own
user tables and the canonical-data mirror both live there. The mirror is rebuilt
from git; if it's ever wrong, the fix is a PR to this repo, not a manual DB edit.

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
collection: base-set
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
top-level fields (`id`, `name`, `type`, `collection`) are structural and validated
the same way everywhere.

### Curation workflow

1. A curator (human, or an AI agent running a skill) branches, edits or adds entity
   files, updates `AGENTS.md`/template if the collection's conventions changed.
2. Opens a PR. CI runs the validator (schema conformance, UUID uniqueness/format,
   required files present).
3. Review — human, and/or an AI review pass (a natural evolution of the existing
   `curator-audit-*` skills in the `wills-attic` repo, pointed at a diff instead of
   a live query).
4. Merge to `main`.
5. A sync job picks up the diff and upserts the changed entities into the Supabase
   mirror, keyed on `id`. Because git is the source of truth, the mirror can always
   be thrown away and rebuilt from a full repo scan — it's a cache, not a record.

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
  Supabase directly."** The only legitimate writer of those tables is the sync job.
  The only way to change canonical data is a PR to this repo.
- Because attic-api and the mirror now share a Postgres instance, that needs an
  explicit safeguard instead of an implicit one (there's no longer a different
  hostname to protect it): a separate DB role for the sync job vs. attic-api's own
  role (mirror tables `SELECT`-only for attic-api), and/or a lint check.
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
- **Phase 2** — build the sync job (git → Supabase mirror tables). Stand up the
  mirror schema in Supabase as new tables alongside the old ones. No cutover yet.
- **Phase 3** — migrate one real, already-verified collection into the new format
  (candidate: "Base" Pokémon — recently audited complete at 102/102 cards) and run
  the sync end-to-end against a non-prod mirror; diff against the live GraphQL data
  for parity before trusting it further.
- **Phase 4** — migrate attic-api's own app tables (`users`, `user_items`,
  `wishlists`, `user_collection_favorites`, `api_tokens`) from the separate Railway
  Postgres into this same Supabase project. Point attic-api's DB connection at it.
- **Phase 5** — cut over attic-api's canonical-data reads from
  `DatabaseOfThingsService` (GraphQL-over-HTTP) to direct SQL against the mirror
  tables in the same connection.
- **Phase 6** — decommission the old Supabase GraphQL surface (pg_graphql exposure)
  and the separate Railway app-Postgres. Finalize the images answer.

The standalone Agent-SDK curator service remains the long-term target for running
audits/updates at scale (see `wills-attic/docs/plans/2026-07-12-ai-curator-system-design.md`)
— it just changes what it does at the point of action: instead of calling MCP write
tools against Postgres, it opens a PR against this repo.

## Open questions

- Entity file format: YAML chosen for readability/diffability/comments; revisit if
  schema validation tooling or merge-conflict rates make a different format
  preferable.
- Whether the existing MCP server's 26 tools get repurposed as read-only research
  helpers for curators (search/lookup while drafting a PR) or retired in favor of
  plain file edits.
- Where the sync job runs (a GitHub Action on merge vs. a small Railway worker
  polling the repo) — affects how quickly the mirror reflects a merged PR.
- Full resolution of the images question above.
