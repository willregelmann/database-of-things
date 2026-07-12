# Database of Things

[![CI](https://github.com/willregelmann/database-of-things/actions/workflows/ci.yml/badge.svg)](https://github.com/willregelmann/database-of-things/actions/workflows/ci.yml)

A minimal, git-driven database of collectibles — curated by agents and humans
through GitHub pull requests.

## What this is

Database of Things (DBoT) is the canonical collectibles data behind
[Will's Attic](https://www.my-attic.online). Its source of truth is
[`collections/`](collections/) in this repo: one YAML file per item, organized
into directories by category. There's no database to write to — curation
*is* opening a pull request.

Each category carries its own curation guidance right next to its data:

- **`AGENTS.md`** — naming conventions, how to identify items, how to verify a
  collection is complete, common pitfalls specific to that category.
- **`template.schema.json`** — a JSON Schema for that category's item
  attributes, enforced by CI on every PR.

See [`docs/dbot-target-architecture.md`](docs/dbot-target-architecture.md) for
the full design and where this is headed.

## Repository structure

```
collections/                  # the data — see collections/README.md
  pokemon-tcg/
    AGENTS.md
    template.schema.json
    original-series/
      base-set/
        charizard-4-102.yaml
        ...
tools/collections-validate/   # CI validator: schema conformance, UUID
                               # uniqueness, required-file presence
.claude/skills/collections-curate/  # agent tooling for adding/editing entries
docs/                          # design docs
```

## Adding or editing an entry

Use the `collections-curate` skill if you're working with Claude Code — it
resolves the right template and `AGENTS.md`, generates a UUID, writes the file
in the right place, and validates before you open a PR. See
[`collections/README.md`](collections/README.md) for the file format and
[`collections/pokemon-tcg/AGENTS.md`](collections/pokemon-tcg/AGENTS.md) for an
example of category-specific curation hints.

Otherwise: add or edit YAML files by hand, following the conventions in the
category's `AGENTS.md`, and validate before opening a PR:

```bash
cd tools/collections-validate
npm install   # first time only
npm run validate
```

## Contributing

This is a curator-reviewed project — contributions are welcome as pull
requests:

1. Read the target category's `AGENTS.md` before naming or structuring
   anything.
2. Run the validator; it must pass before review.
3. Open a PR against `main`. It won't be merged automatically — expect
   review.

## License

MIT License — see [LICENSE](LICENSE).
