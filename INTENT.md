## Objective

Build and maintain a freely reusable catalog of collectibles — what exists,
in which sets, released when — aiming to be the most comprehensive such catalog
on the Internet. Curation is deliberately governed rather than transactional:
there is no database to write to, so every change is a pull request that can be
reviewed, rejected, and traced.

### Secondary Goals

- Leverage GitHub as a file database with no external platform

## Audience

- **Consumers** — anyone building on the catalog, who needs stable
  identifiers and accurate enumeration, and needs it without asking permission
  or attributing anyone
- **Maintainers** — anyone who wants review authority over a particular
  collection, and can claim it without changing how the rest of the catalog
  operates
- **Contributors** - anyone who wants to augment collection information
  through standard GitHub operations

## Success Criteria

1. Coverage extends across many collectible categories at comparable depth,
   rather than concentrating in one.
2. Every merged change has had each of its factual claims independently
   re-verified before merge, whoever proposed it.
3. A person can claim review authority over any single collection without
   altering how the rest of the catalog operates.
4. Every entity resolves: no duplicate identifiers, no dangling tag
   reference, no collection directory missing its own record.

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