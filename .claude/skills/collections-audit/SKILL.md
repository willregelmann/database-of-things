---
name: collections-audit
description: Audit a single collection directory under collections/ (one that has its own _collection.yaml — a domain family, category, series, set, or any nested grouping) for CLAUDE.md conformance and, via web search, for completeness/accuracy of its own _collection.yaml and its direct contents. Use when a curator wants to check whether an existing collection is correct, not to add or edit entries (use collections-curate for that).
---

# Collections Audit

Read-only quality check for one collection directory under `collections/` —
does it follow this repo's own documented conventions, and does it actually
match reality? Complements `collections-curate` (which writes entity files)
rather than replacing it: this skill finds problems and reports them; fixing
what it finds is a separate, explicitly-requested step.

**Scope: exactly one level per invocation.** Audit the target directory's
own `_collection.yaml` and its *direct* children only — either the item
files it contains, or the immediate nested collection directories, never
both deep-dived at once (see [`collections/CLAUDE.md`](../../../collections/CLAUDE.md)'s
"Collection shape" section). Do not open, read the CLAUDE.md of, or verify
the contents of any grandchild collection. If the caller wants a whole
category or the whole tree checked, that means invoking this same
single-level process once per directory, not recursing automatically —
only do that when explicitly asked (e.g. "audit the whole `original-series/`
tree").

## Hard rules

- **Read-only by default.** Report findings; don't edit entity files,
  `CLAUDE.md`, or `template.schema.json`, and don't open a PR, unless the
  user explicitly asks you to fix what you found.
- **Don't recurse into child collections** unless the user directs it.
- **Cite a source for every completeness/accuracy claim.** Every finding
  from Steps 2–3 needs a URL (or a quoted CLAUDE.md rule) backing it —
  no unsourced "this looks wrong."
- **Don't fabricate fixes for gaps you find.** If a field is missing or
  unverifiable, report it as a gap — same "leave it off / flag it rather
  than guess" philosophy the curation guidance itself uses, not something
  to paper over during an audit.

## Step 0: Resolve the target and its shape

1. Confirm the target directory exists under `collections/` and has its own
   `_collection.yaml`. If it doesn't, this isn't a valid audit target — stop
   and say so (it's either an item file or a directory missing a required
   record, which `npm run validate` would already flag).
2. List the target's direct children and classify them: nested collection
   directories (each with its own `_collection.yaml`) or leaf item files.
   Per "Collection shape," expect one or the other, rarely both — note it
   as a Step 1 finding if it's mixed without an apparent reason.
3. Identify the **category root**: walk up from the target until you reach
   the directory that sits directly under a domain-family directory (or
   directly under `collections/`, if the category has no family). That
   directory is the category root for this lineage — e.g. for
   `trading-card-games/pokemon-tcg/original-series/base-set/`, the category
   root is `pokemon-tcg/`.

## Step 1: Gather the applicable CLAUDE.md chain, then check conformance

Read, in order:

1. Root [`collections/CLAUDE.md`](../../../collections/CLAUDE.md) — always,
   regardless of level; it states its own guidance applies everywhere in
   the tree.
2. The domain family's `CLAUDE.md`, if the category sits under one.
3. The category root's own `CLAUDE.md` (per Step 0.3) — this is the
   "root-level category collection" ceiling for this lineage; you don't
   need a sibling category's `CLAUDE.md`.
4. Any intermediate directory's own `CLAUDE.md` between the category root
   and the target (nested overrides are rare but do occur).
5. The target directory's own `CLAUDE.md`, if it has one.

These layer additively — each level adds detail on top of the previous
ones, it doesn't replace them (this is exactly what every category
`CLAUDE.md` says about its relationship to the root one).

Then check the target's own `_collection.yaml` and its direct children
against everything gathered:

- Required fields (`id`/`name`/`type`) and no forbidden
  `collection:`/`parent_collection:` field — run
  `cd tools/collections-validate && npm run validate` for this mechanically
  rather than checking it by hand; treat a failure here as a Step 1 finding.
- `_collection.yaml` has `type: collection` plus whatever fields the
  category convention requires on every collection record (e.g. Pokémon
  TCG's `category` + `description` — see that category's `CLAUDE.md`).
- File/directory naming matches the documented scheme (slugification,
  canonical-number prefix and zero-padding width, disambiguation rules).
- `date` format, precision, and rollup-from-earliest-child rules followed
  (root `CLAUDE.md`'s "Dates" section).
- `tags`, if present: lowercase-hyphenated, rarely more than 5, not
  restating the hierarchy or a structured attribute (root `CLAUDE.md`'s
  "Tags" section).
- `image.source_url` / logo guidance followed where it applies (root
  `CLAUDE.md`'s "Logos" section) — authoritative source, belongs to the
  entity itself, actually resolves.
- "Collection shape": not mixing collections and items without reason: not
  approaching/exceeding 1000 items or 100 nested collections without a
  natural subdivision already in place.
- Category-specific pitfalls documented in its `CLAUDE.md` that apply at
  this level (numbering quirks, enum correctness, known exclusions, etc.).

## Step 2: Is the target's own `_collection.yaml` complete and accurate?

Web-search for the collection this directory represents (the set,
series, product line, etc. — not its individual contents) and verify, citing
sources:

- `name` — matches the official name.
- `date` — correct first-release date at the right precision (not padded
  beyond what's actually sourceable).
- `description` / `category` / other category-convention fields — accurate
  and not stale.
- `image.source_url` — resolves (spot check with e.g.
  `curl -o /dev/null -w '%{http_code}'`) and is actually this entity's own
  mark, not a franchise/licensor's.
- Anything the category convention says every collection record should
  carry but this one is missing.

## Step 3: Is the target's content complete and accurate?

This means the target's **direct** children only — the checklist one level
down, not anything inside a nested collection.

- **Completeness**: find (or reconstruct) the authoritative checklist for
  this level — e.g. a set's full card list, a product line's full release
  list, a category's full list of official sub-collections. Confirm every
  real entry has a corresponding file/directory, and flag anything present
  in this repo that shouldn't be (fabricated, misfiled, or belongs
  elsewhere).
- **Accuracy**: spot-check key fields (`name`, canonical
  identifier/`attributes.number`-equivalent, `date`) on a sample of
  children against the source. For a small directory, check everything;
  for a large one (approaching the ~1000-item soft ceiling), a
  representative sample is enough for a routine audit — call out that
  it's a sample, and do an exhaustive pass only if the user asks for a
  deep audit.
- If children are nested collections rather than items, this step checks
  only that the *list* of nested collections is complete and correctly
  named/scoped — not each one's own internal completeness (that's that
  child's own audit, a separate invocation).

## Step 4: Report

Summarize findings in three sections matching the steps above —
**CLAUDE.md conformance**, **`_collection.yaml` accuracy**, **content
completeness/accuracy** — each finding with its source (a quoted rule or a
URL) and a suggested fix. Don't apply fixes unless asked. If a section has
no findings, say so explicitly rather than omitting it, so a clean result
reads as "checked, nothing found" rather than "not checked."

## Checklist

- [ ] Confirmed the target has its own `_collection.yaml` before starting
- [ ] Classified direct children (items vs. nested collections) and noted
      any unexplained mixing
- [ ] Read the full applicable `CLAUDE.md` chain (root → family → category
      → any intermediate → own), not just the nearest one
- [ ] Ran `npm run validate` as part of the conformance check
- [ ] Every completeness/accuracy claim has a cited source
- [ ] Did not recurse into child collections unless explicitly asked
- [ ] Did not edit files or open a PR — this is a report, not a fix
