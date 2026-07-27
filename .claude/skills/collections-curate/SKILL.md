---
name: collections-curate
description: Add or edit entities/collections in the new file-based collections/ format (the GitHub-repo-as-source-of-truth model). Use when a curator wants to add a card/item, add a new collection, or validate pending changes before opening a PR.
---

# Collections Curate

Maintains `collections/` — the file-based source of truth. Its format and the
primitives it's built from are documented in
[`collections/README.md`](../../../collections/README.md) and
[`docs/primitives/`](../../../docs/primitives/) (`COLLECTION.md`, `ITEM.md`,
`COMPONENT.md`, `TAG.md`). This is the tooling a curator (human or AI) uses to
add or edit entries.

There is no database behind this repo. An earlier design kept the catalog in
Supabase with the files as an export target; that was retired, and the files
are now the only source of truth — curation *is* opening a pull request.

## Hard rules

- **Output is files under `collections/` and `tags/`, nothing else.** No live
  service, no database, no external write of any kind.
- **Never push or open a PR without the user confirming first.** This repo has
  not been granted git autonomy — always ask before `git push` or
  `gh pr create`. (The one scoped exception is the `collections-audit-review`
  skill, which may merge the audit job's own `audit-finding` PRs; it does not
  extend to this skill.)
- **Always run the validator before considering a change done.**

## Workflow: add an entity to an existing collection

1. Find the target collection directory under `collections/` (e.g.
   `collections/trading-cards/pokemon-tcg/original-series/base-set/`).
2. Read the nearest ancestor `CLAUDE.md` (walk up until you find one) for
   naming/identification conventions specific to this category.
3. Read the nearest ancestor `template.schema.json` to know what `attributes`
   fields are expected/allowed.
4. Generate a new id: `uuidgen`. Never reuse an id, never hand-pick one.
5. Write the entity YAML file following the format in `collections/README.md` and
   the category's `CLAUDE.md` naming convention.
6. Run the validator:
   ```bash
   cd tools/collections-validate && npm run validate
   ```
7. Fix any errors it reports before considering the entity done.

## Workflow: add a new collection

1. Decide what kind of collection this is:
   - **A new category** (a specific collectible line, e.g. a new card game or
     coin series) — needs its own `CLAUDE.md` + `template.schema.json`.
   - **A set nested under an existing category** (e.g. a new expansion) —
     usually just needs its own `_collection.yaml` and inherits the rest.
   - **A new domain family** (a broad grouping like `trading-cards` that
     will hold multiple categories) — only when the category doesn't fit any
     existing family; see `collections/README.md` for when families are
     warranted.
2. For a new category: decide whether it belongs inside an existing domain
   family (e.g. `collections/trading-cards/<line>/`) or directly under
   `collections/`. Create the directory, write `CLAUDE.md` (curation hints —
   identification scheme, completeness-checking approach, naming convention,
   known pitfalls — follow the shape of
   `collections/trading-cards/pokemon-tcg/CLAUDE.md`), write
   `template.schema.json` (JSON Schema for `attributes`), and `_collection.yaml`
   (`type: collection`, plus a `description`).
3. For a nested set: create the directory (inside its parent category/set
   directory — that placement *is* the parent relationship, don't add a
   `parent_collection` field) and its `_collection.yaml` only (`type: collection`,
   plus whatever descriptive fields fit — see
   `collections/trading-cards/pokemon-tcg/original-series/base-set/_collection.yaml`
   for the shape).
4. For a new domain family: create the directory, write `CLAUDE.md` (what
   belongs in this family, pointer to a worked-example category), a minimal
   permissive `template.schema.json` (required by the validator even though
   the family's own `_collection.yaml` has no `attributes` to check — see
   `collections/trading-cards/template.schema.json`), and `_collection.yaml`.
4. Run the validator.

## Workflow: validate pending changes

```bash
cd tools/collections-validate && npm run validate
```

Reports, per file: missing/empty required fields (`id`, `name`, `type`), invalid or
duplicate `id`, missing `CLAUDE.md`/`template.schema.json` (own or inherited),
missing `_collection.yaml`, a stray `collection:`/`parent_collection:` field
(parent membership comes from directory position, not a field), and schema
violations in `attributes`.

## Checklist

- [ ] Read the applicable `CLAUDE.md` before naming/structuring anything
- [ ] Generated a fresh UUID for any new entity — never reused or hand-picked
- [ ] Ran the validator and it passed
- [ ] Wrote only files under `collections/`/`tags/` — no live service
- [ ] Did not push or open a PR without asking the user first
