# Variant

> **Status: proposed, not adopted.** No `variants` field exists in the catalog
> today and the validator doesn't implement any of this. The other files in
> this directory describe the model as built; this one describes a gap and a
> proposed way to close it. Adopting it has real costs — see
> [If adopted](#if-adopted).

A **variant** is a physically distinguishable version of an [item](ITEM.md)
that a collector may or may not count as a separate thing to own: a reverse
holo printing of a card, an alternate cover of a comic issue, a colorway of a
figure, a regional printing with a different number on the back.

## Why it needs to be a primitive

Each existing primitive is defined by a **completion rule**, not by its data
shape:

| primitive | rule |
|---|---|
| [Collection](COLLECTION.md) | owning **every** item constitutes owning the collection |
| [Component](COMPONENT.md) | owning **every** component does *not* constitute owning the item |
| **Variant** | owning **any one** variant constitutes owning the item |

Collection is "all of". Component is "all of, and still not enough". Variant
is **"any one of"** — and nothing in the model expresses it. That's the gap.
Reverse holos and alternate covers are currently uncatalogued anywhere,
because they're not items (a set-completionist doesn't need them), not
components (they aren't parts of anything), and not tags.

**The decisive property is that the completion rule isn't the catalog's to
make.** Whether a reverse holo is a separate collectible is a fact about the
*collector*, not about the card. Some chase one of each card; some chase every
printing of every card — which the trading-card world already calls a **master
set**, so the distinction is community-standard vocabulary rather than
something invented here. A primitive that records the variant's existence
while leaving the completion rule to the consumer serves both. Modelling
variants as items serves only the second and silently inflates every set's
size; modelling them as nothing serves only the first.

## Ownership semantics

- **Owning any one variant of an item constitutes owning that item.** A set
  completed with reverse holos is a completed set.
- **Owning every variant is a distinct, stricter goal**, and one the catalog
  should be able to express without making it the default.
- **A variant is never a member of a collection.** Collection membership runs
  through the item; a collection's size is its item count, unaffected by how
  many variants those items have.

## Where it lives: inline on the item

A variant is **not** its own file. It's an entry in the item's top-level
`variants` array, stating only what differs from the item:

```yaml
id: 3f4334f3-6a41-45fb-a1c1-dcf44566491e
name: Charizard
type: card
date: "1999-01-09"
attributes:
  number: "4/102"
  rarity: Rare Holo
  illustrator: Mitsuhiro Arita
variants:
  - id: 9a2c1e77-4b60-4c1a-9f1e-2d7c5a83e011
    name: Reverse Holo
    attributes:
      finish: Reverse Holo
```

Two reasons, and the first is the important one.

**Duplication is what causes drift.** A variant that repeated `name`, `type`,
`date`, `illustrator` and everything else would put the same fact in two
places with nothing keeping them consistent. Stating only the delta means a
correction to the item is automatically a correction to all its variants.
This is the whole reason the field is inline rather than a
`variant_of: <id>` pointer between two full entity files.

**A variant has no parentage of its own.** A [component](COMPONENT.md) exists
apart from its item — a minifig is sold loose, filed in its own directory,
referenced by many sets — so it earns a file, and directory position gives it
a parent. A variant cannot exist apart from its item; it *is* that item,
differently finished. It can't sit in another collection, so it has no
directory position to occupy, and this repo expresses parentage by directory
position alone (there is deliberately no `parent_collection` field — see
[ITEM.md](ITEM.md)). An entity with no possible parentage shouldn't get a
file.

## Fields

A variant entry carries:

- **`id`** — required. A real UUID in the same namespace as every other
  entity, so a consumer can record owning *specifically* this variant.
  Addressability is the point; a variant without an id can't be tracked,
  which defeats the primitive.
- **`name`** — required. The variant's **distinguishing label**, not a full
  restatement: `Reverse Holo`, not `Charizard (Reverse Holo)`. Consumers
  compose the display form from the item's name plus this.
- **`date`**, **`attributes`**, **`image`** — optional, and each *overrides*
  the item's when present. `attributes` merges key-by-key over the item's, so
  a variant states only the keys that differ.

A variant does **not** carry `type` (it's the item's), `tags` (franchise
resolves from the item's ancestry), or `components`.

## The item is the default version

The item record *is* the standard version; variants are deltas from it. A
plain Charizard isn't listed as a variant of itself.

Where a source treats no version as canonical, the category's own `CLAUDE.md`
picks which one the item represents and says so — the same kind of call as
choosing which edition a collection covers.

## Validator rules

- Variant `id`s participate in the same global uniqueness check as every
  other entity `id`.
- **Duplicate `id`s within one `variants` array are an error** — unlike
  [`components`](COMPONENT.md), where a repeat meaningfully represents owning
  two of something. Two identical variants of one item is not a thing.
- A variant's merged `attributes` validate against the same
  `template.schema.json` the item resolves — a variant can't introduce a key
  the category's schema doesn't allow.
- `variants` is rejected on a `_collection.yaml`. Collections don't have
  variants; their items do.

## What is not a variant

- **A reprint in a later, separately-named set.** That's its own item in its
  own collection, with its own number. Heavily-reprinted cards legitimately
  appear across dozens of sets.
- **An edition from a different publisher or manufacturer.** Those sit under
  a different brand-tier parent, and a variant can't have a different parent
  than its item — so Dark Horse's *Akira* and Kodansha's are separate
  collections, not variants (see
  [`collections/comics-and-manga/CLAUDE.md`](../../collections/comics-and-manga/CLAUDE.md)).
- **A different product entirely** that happens to depict the same character.
- **Condition or grading.** A graded slab isn't a variant; it's the same
  object with a third-party assessment attached.

## If adopted

Costs, stated plainly, because they're not small.

**The validator, the MCP tool surface and any consumer all need to learn the
field.** `get_item_details` would need to return variants; ownership tracking
would need to accept a variant `id` where it currently accepts an item `id`.

**It supersedes the "separate entities per printing" decision** taken for
Yu-Gi-Oh. `LOB-001`, `LOB-E001`, `LOB-A001` and `LOB-EN001` are one card in
four printings, so
`collections/trading-cards/yu-gi-oh/legend-of-blue-eyes-white-dragon/`
would collapse from 481 files across four printing directories to **126 items
carrying three or four variants each**. That is a reversal of merged work, and
it should be weighed as such.

Two things argue it's the better model even so. It fixes a real awkwardness —
the European printing has 103 cards, not 126, which under separate-items makes
the set's size ambiguous, whereas under variants the set is plainly 126 items
of which 103 have a European variant. And it dissolves the 1st Edition /
Unlimited question that blocked filing entirely: those are variants, and
whether they count separately is the collector's call, which is exactly what
couldn't be resolved by picking one answer.

**It probably tidies existing filename conventions** — Squishmallows'
dash-suffixed colorways and Funko's variant suffixes both encode variance in
filenames today. Neither should be swept in automatically; each is a
per-category call, and `attributes`-level handling may still be right where
the "variance" is really a distinct release.

**It does not settle where variance ends.** That stays a per-category
judgement, per
[`collections/CLAUDE.md`](../../collections/CLAUDE.md#collectibles-not-products).
This primitive says *how* to express a variant once a category decides
something is one.
