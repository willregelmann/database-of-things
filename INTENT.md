## Purpose

Database of Things is a freely reusable catalog of collectibles — what exists,
in which sets, released when — aiming to be the most comprehensive such catalog
on the Internet. Curation is deliberately governed rather than transactional:
there is no database to write to, so every change is a pull request that can be
reviewed, rejected, and traced.

It grows and self-corrects through AI agents that find collectible data and
propose changes. The intent is full autonomy: a change lands on the strength of
independent verification rather than human attention, and human review is
something a person opts into for a collection they choose to steward, not a step
the catalog depends on. Breadth is opened deliberately rather than discovered: a
category is scaffolded with its own curation conventions before anything is
catalogued in it. The catalog is released CC0 for anyone to consume; no single
downstream application defines its scope.

## Users

- **Data consumers** — anyone building on the catalog, who needs stable
  identifiers and accurate enumeration, and needs it without asking permission
  or attributing anyone
- **Curating agents** — autonomous and human-directed alike, which need each
  category's conventions to be discoverable from the data itself rather than
  from a maintainer
- **The maintainer-curator** — sets the catalog's direction and holds final
  authority over it, without being a required step in its operation
- **Collection stewards** — anyone who wants review authority over a particular
  collection, and can claim it without changing how the rest of the catalog
  operates
- **Prospective outside contributors** — propose changes by the same path and
  through the same gate as the catalog's own agents; the door is open in
  principle rather than actively sought

## Success Criteria

Falsifiable. If every one of these held, the project has achieved its intent.

1. Coverage extends across many collectible categories at comparable depth,
   rather than concentrating in one.
2. An agent can extend coverage into a category that does not yet exist, without
   a human authoring that category's conventions first.
3. The catalog can grow and correct itself indefinitely without human
   intervention.
4. Every merged change has had each of its factual claims independently
   re-verified before merge, whoever proposed it.
5. A person can claim review authority over any single collection without
   altering how the rest of the catalog operates.
6. Every entity resolves: no duplicate identifiers, no dangling tag or component
   reference, no collection directory missing its own record.
7. Every catalogued image is attributed to where it is hosted, and every
   category names the authoritative sources its facts should be drawn from.
8. A curator arriving at any category can determine what belongs in it, how to
   name it, and how to tell when it is complete — without asking anyone.

## Non-Goals

- **Exhaustive metadata** — depth of detail is what source links are for;
  coverage is preferred over completeness of fields
- **Market or pricing data** — this is a catalog, not a marketplace
- **Hosting or redistributing images** — the catalog records where an image
  lives, never a copy of it
- **Being authoritative** — the data is offered as-is and is not a substitute
  for the sources it cites
- **Serving any one downstream application** — consumers do not get to shape
  what is cataloged or which fields exist
- **Completion tracking as a purpose** — "owning every item constitutes owning
  the collection" is a modeling rule for where the component/item boundary
  falls, not a service the catalog sets out to provide

## Open Questions

| # | Question | Why it matters | Status |
|---|----------|----------------|--------|
| 1 | How does an agent bootstrap a genuinely new category, given that authoring curation conventions is deliberately outside the tool surface's scope? | Criteria 2 and 3 are both unreachable until this is answered; it is the binding constraint on autonomy as well as on breadth. | Open |
| 2 | Is uniform random sampling the right way to allocate audit effort when breadth is the goal? | The audit ledger exists to make this answerable with data rather than argument. | Open |
| 3 | With verification the sole barrier regardless of who proposes a change, what prevents a change engineered to satisfy the verifier rather than to be true? | Provenance no longer gates anything, so the verifier is the entire trust boundary. | Open |
| 4 | The catalog is described as "community-curated" — what has to exist before outside participation is discoverable, and is building it a goal? | The gate is now identical for everyone, but nothing advertises the door or explains how stewardship is claimed. | Open |

---

Discovered 2026-07-25.
