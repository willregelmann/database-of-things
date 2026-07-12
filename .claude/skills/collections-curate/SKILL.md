---
name: collections-curate
description: Add or edit entities/collections in the new file-based collections/ format (the GitHub-repo-as-source-of-truth model). Use when a curator wants to add a card/item, add a new collection, or validate pending changes before opening a PR.
---

# Collections Curate

Maintains `collections/` — the file-based source of truth described in
`docs/dbot-target-architecture.md`. This is the tooling a curator (human or AI)
uses to add or edit entries, not a way to write to the live Supabase database
directly (there's no sync job yet — see Phase 2 in that doc).

## Hard rules

- **Never write to Supabase from this skill.** Output is files under `collections/`
  only.
- **Never push or open a PR without the user confirming first.** This repo has
  not been granted git autonomy — always ask before `git push` or
  `gh pr create`.
- **Always run the validator before considering a change done.**

## Workflow: add an entity to an existing collection

1. Find the target collection directory under `collections/` (e.g.
   `collections/pokemon-tcg/base-set/`).
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

1. Decide if this is a new top-level category (needs its own `CLAUDE.md` +
   `template.schema.json`) or a set nested under an existing category (usually
   just needs its own `_collection.yaml` and inherits the rest).
2. For a new top-level category: create the directory, write `CLAUDE.md`
   (curation hints — identification scheme, completeness-checking approach, naming
   convention, known pitfalls — follow the shape of
   `collections/pokemon-tcg/CLAUDE.md`), write `template.schema.json` (JSON Schema
   for `attributes`), and `_collection.yaml` (`type: collection`, plus a
   `category`/`description`).
3. For a nested set: create the directory (inside its parent category/set
   directory — that placement *is* the parent relationship, don't add a
   `parent_collection` field) and its `_collection.yaml` only (`type: collection`,
   plus whatever descriptive fields fit — see
   `collections/pokemon-tcg/base-set/_collection.yaml` for the shape).
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
- [ ] Did not write to Supabase or any live service
- [ ] Did not push or open a PR without asking the user first
