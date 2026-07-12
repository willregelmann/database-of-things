# Database of Things

[![CI](https://github.com/willregelmann/database-of-things/actions/workflows/ci.yml/badge.svg)](https://github.com/willregelmann/database-of-things/actions/workflows/ci.yml)

A public, file-based catalog of collectibles data — trading cards, figures,
comics, video games, and more.

## What this is

Database of Things (DBoT) is a plain git repo, not a database or a service.
Canonical data lives as YAML files under `collections/`; curators (human or AI)
propose changes as pull requests; a CI job validates every change. There's no
server, no database, and no secrets in this repo — anyone can clone it and use
the data for anything.

See [`docs/dbot-target-architecture.md`](docs/dbot-target-architecture.md) for
the full design and how consumers (like Will's Attic) are expected to sync from
this repo on their own terms.

## Repo layout

```
collections/
  <category>/
    AGENTS.md                 # curation hints for this whole category
    template.schema.json      # JSON Schema for item `attributes`
    _collection.yaml          # this collection's own entity record
    <set>/
      _collection.yaml        # nested collection; inherits AGENTS.md + template
      <item>.yaml
tools/collections-validate/    # the CI validator
docs/                          # architecture and design docs
```

## Entity format

One YAML file per entity:

```yaml
id: 3f4334f3-6a41-45fb-a1c1-dcf44566491e   # stable UUID, generated once
name: Charizard
type: card
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

A file's parent collection is wherever it sits in the directory tree — there's
no `collection:`/`parent_collection:` field to keep in sync.

## Adding or editing an entry

1. Find (or create) the target collection directory under `collections/`.
2. Read the nearest `AGENTS.md` for that category's naming/identification
   conventions, and the nearest `template.schema.json` for its `attributes`
   shape.
3. Generate a fresh UUID (`uuidgen`) — never reuse or hand-pick one.
4. Write the entity YAML file.
5. Validate:
   ```bash
   cd tools/collections-validate
   npm install   # first time only
   npm run validate
   ```
6. Open a pull request. CI runs the same validation on every PR that touches
   `collections/**`.

Full details: [`collections/README.md`](collections/README.md) and the
`collections-curate` skill under `.claude/skills/` (for curators running in
Claude Code).

## License

MIT License — see [LICENSE](LICENSE).
