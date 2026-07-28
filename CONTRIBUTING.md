# Contributing to Database of Things

There's no database to write to. **Curation *is* opening a pull request** —
every entry in this catalog is a YAML file under [`collections/`](collections/),
and every change to it arrives as a PR.

Humans and AI agents are both first-class contributors here. The catalog is
designed to grow primarily through agents web-searching for collectible data
and opening PRs, so the conventions below are written to be followed by either.

## Before you write anything: read the CLAUDE.md chain

**Curation guidance travels with the data.** Rather than one central style
guide, each level of the tree carries its own `CLAUDE.md` next to the entity
files it governs, and they compose: the root
[`collections/CLAUDE.md`](collections/CLAUDE.md) applies everywhere, a
category's adds its specifics on top, a line's adds more.

Walk up from wherever you're adding a file and read every `CLAUDE.md` you
pass. They exist because someone already hit the trap you're about to.
[`collections/trading-cards/pokemon-tcg/CLAUDE.md`](collections/trading-cards/pokemon-tcg/CLAUDE.md)
is the worked example.

## The principle that settles most questions

**DBoT catalogues collectibles, not products.** The entity is the individual
physical thing someone owns and points at — one card, one figure, one issue —
not the commercial unit it was sold as. Deduplicate on **physical uniqueness,
not on UPC or packaging**.

That one rule decides a surprising amount: whether a multipack gets its own
entry (no — file the figures), whether "Booster Pack" is a directory tier (no
— it describes the box, not the card), and whether two entries are the same
thing. See
[`collections/CLAUDE.md`](collections/CLAUDE.md#collectibles-not-products).

## Where a file goes

Every path has the same shape, documented at
[`collections/CLAUDE.md`](collections/CLAUDE.md#tree-shape):

```
<category>/<brand>[/<line>[/<subline>…]]/<item>
```

Two rules govern the optional tiers: a tier must be **named by the brand or
standard in the collecting community** — never invented to make a category
look symmetrical — and **a brand is never split across sibling directories**.

An entity's parent is the directory it sits in. There is no
`collection:`/`parent_collection:` field, and the validator rejects one if it
finds it.

## Adding an entry

**With Claude Code**, use the `collections-curate` skill — it resolves the
right template and `CLAUDE.md`, generates a UUID, writes the file in the right
place, and validates.

**By hand:**

1. Find the target directory and read its `CLAUDE.md` chain.
2. Read the nearest `item-attributes.schema.json` — it defines what `attributes` are
   allowed, and the validator enforces it.
3. Generate a fresh id with `uuidgen`. **Never reuse or hand-pick one.**
4. Write the file per [`collections/README.md`](collections/README.md) and the
   category's naming convention.
5. Validate (below).

## Adding a new collection

New lines arrive in **two phases** — see
[`collections/CLAUDE.md`](collections/CLAUDE.md#scaffolding-a-new-collection):

- **Phase 1 — scaffold.** Create the directory and its `_collection.yaml`,
  inheriting the parent's `CLAUDE.md` and `item-attributes.schema.json`. **An itemless
  `_collection.yaml` is a legitimate contribution** — it records that something
  exists and hasn't been curated yet, which beats the catalog silently implying
  it doesn't exist.
- **Phase 2 — author its conventions.** Its own `CLAUDE.md` and
  `item-attributes.schema.json`, required *before its first item* is filed.

The order is deliberate: an identification scheme is far easier to get right
while holding real product data than in the abstract.

## Sourcing standards

This is where contributions are most often sent back.

- **Cite a source for anything you assert.** If you can't verify it, leave it
  out — a gap is recoverable, a confidently wrong entry is worse, because
  nothing downstream flags it.
- **Cross-reference where the category says to.** Several require two
  independent sources before filing; the category's `CLAUDE.md` says which and
  names the good ones.
- **Don't fabricate precision.** `date` records first release, at whatever
  precision the source actually supports — `"1999"`, `"1999-06"`, and
  `"1999-06-30"` are all valid. A card known only to have shipped "in 1999"
  stays `"1999"`. If nothing reliable exists, **leave the field off** rather
  than guessing; that's a gap to close later, not something to invent now.
- **Verify image URLs resolve** before considering an entry done, and take
  them from the rights-holder or a well-maintained reference rather than
  hand-constructing one.

## Descriptions: write original prose

The catalog data is released into the public domain under **CC0 1.0**
([LICENSE-DATA](LICENSE-DATA)), and that only works if the text is ours.

**State facts freely — but never paste or lightly reword source text.**
Copying a description from a wiki, a fan database, or a manufacturer's
marketing copy imports that source's licence; Bulbapedia's CC BY-NC-SA, for
instance, is incompatible with CC0. Facts carry no licence, original
expression over those facts does. A description written by an AI curator is
fine as long as it's genuine synthesis rather than regurgitated source prose.

Keep it factual and brief — a few sentences. If there's nothing non-obvious to
say beyond what the name and hierarchy already convey, leave `description` off.

## Validating

Required before review. CI runs the same check on every PR, including stacked
ones.

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

It checks required fields, UUID format and uniqueness, `attributes` against the
resolved schema, referential integrity of `tags`, presence of
`_collection.yaml`, and that a directory holding entity files has a `CLAUDE.md`
and `item-attributes.schema.json` — own **or inherited**.

## How PRs get merged

Open against `main` and expect human review. **Outside contributions are never
merged automatically.**

One narrow exception, documented so it isn't surprising: an hourly autonomous
job audits a randomly chosen collection and opens its own PRs labelled
`audit-finding`. A second scheduled job reviews *those*, re-verifying every
claim against an independently run search, and may merge them once CI is
green. That authority is scoped to machine-generated `audit-finding` PRs from a
matching `audit/<hash>` branch and to nothing else — see
[`.claude/skills/collections-audit-review/`](.claude/skills/collections-audit-review/).

## Owned collections

Some collections have a maintainer listed in
[`.github/CODEOWNERS`](.github/CODEOWNERS), who is asked to review PRs touching
them. **Ownership means someone has taken responsibility for that collection's
conventions and accuracy — it doesn't make the collection off-limits.**
Contributions to owned collections are welcome and are simply reviewed by the
person who knows their pitfalls.

## Scope

Worth knowing before investing effort in a large addition:

**In scope** — collectibles sold as identifiable product lines, with enough
public documentation to catalogue accurately.

**Not optimising for** — exhaustive metadata (that's what `image` links
are for), or real-time market data. This is a catalog, not a marketplace, and
minimal metadata is a deliberate design choice rather than an unfinished
state. Prefer coverage over depth.

## Reference

- [`collections/README.md`](collections/README.md) — the file format
- [`collections/CLAUDE.md`](collections/CLAUDE.md) — cross-cutting curation rules
- [`docs/primitives/`](docs/primitives/) — the data model (`COLLECTION`, `ITEM`,
  `TAG`)
- [`tags/CLAUDE.md`](tags/CLAUDE.md) — adding a franchise tag
- [`LICENSE`](LICENSE) (code, MIT) and [`LICENSE-DATA`](LICENSE-DATA) (data, CC0)
