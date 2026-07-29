# Database of Things

[![CI](https://github.com/willregelmann/database-of-things/actions/workflows/ci.yml/badge.svg)](https://github.com/willregelmann/database-of-things/actions/workflows/ci.yml)

A minimal, git-driven database of collectibles — curated by agents and humans
through GitHub pull requests.

## What this is

Database of Things (DBoT) is a minimal, git-driven database of collectibles.
Its source of truth is [`collections/`](collections/) in this repo: one YAML
file per item, organized into directories by category. There's no database to
write to — curation *is* opening a pull request.

Each category carries its own curation guidance right next to its data:

- **`CLAUDE.md`** — naming conventions, how to identify items, how to verify a
  collection is complete, common pitfalls specific to that category.
- **`item-attributes.schema.json`** — a JSON Schema for that category's item
  attributes, enforced by CI on every PR.

## Repository structure

```
collections/                  # the data — see collections/README.md
  trading-cards/
    pokemon-tcg/
      CLAUDE.md
      item-attributes.schema.json
      original-series/
        base-set/
          004-charizard.yaml
          ...
tools/collections-validate/   # CI validator: schema conformance, UUID
                               # uniqueness, required-file presence
docs/                          # design docs
```

## Adding or editing an entry

Add or edit YAML files by hand, following the conventions in the category's
`CLAUDE.md`. See [`collections/README.md`](collections/README.md) for the
file format and
[`collections/trading-cards/pokemon-tcg/CLAUDE.md`](collections/trading-cards/pokemon-tcg/CLAUDE.md)
for an example of category-specific curation hints.

Validate before opening a PR:

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

## Contributing

This is a curator-reviewed project — contributions are welcome as pull
requests. **See [CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide,
including sourcing standards, where a file goes, and the CC0 rule on writing
descriptions. The short version:

1. Read the target category's `CLAUDE.md` before naming or structuring
   anything.
2. Run the validator; it must pass before review. CI runs it on every PR.
3. Open a PR against `main` and expect human review — outside contributions
   are never merged automatically.

Some collections have a maintainer listed in
[`.github/CODEOWNERS`](.github/CODEOWNERS) who is asked to review PRs touching
them. That signals who knows a collection's pitfalls, not that it's closed to
contributions.

## License

DBoT is dual-licensed to reflect the two different kinds of content in this
repository:

- **Code** — the validator, MCP server, scripts, skills, and JSON schemas — is
  licensed under the **MIT License** ([LICENSE](LICENSE)).
- **Catalog data** — everything under [`collections/`](collections/) and
  [`tags/`](tags/), including collection-level `description` text — is released
  into the public domain under **CC0 1.0** ([LICENSE-DATA](LICENSE-DATA)). It's
  factual metadata plus original descriptions written for this project; take it
  and use it freely.

The data is factual and the descriptions are original to this project, so CC0
is a clean fit. Two things it does not cover: third-party **trademarks** (the
product and brand names cataloged here belong to their owners) and the
**images** referenced by the `image` field (hosted by third parties, not
redistributed here — the repo only stores URLs). See [DISCLAIMER.md](DISCLAIMER.md)
for details.
