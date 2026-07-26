*Point-in-time comparison, 2026-07-25. Three independent clean-room designs were
commissioned from `INTENT.md` alone and compared against the current design.
Expected to go stale — re-run `reimagine-from-intent` rather than editing this
file.*

## How this was run

Three subagents received an identical brief derived from `INTENT.md` and nothing
else — no project path, no repository access, no technology stack, no file
listing, and no sight of each other's work. They were given the same prompt with
no assigned perspectives or priorities, because variation introduced between
designers is variation that cannot be interpreted afterward. Each was asked to
mark its own decisions as brief-driven or arbitrary.

**What the brief kept as constitutive:** the source of truth is a
version-controlled history in which every change is a reviewable, rejectable,
traceable proposal; and growth happens primarily through AI agents proposing
changes.

**What the brief scrubbed as incidental**, and named as explicitly unconstrained
so the designers had permission to diverge: any particular forge, on-disk layout,
file format, data-model primitives or their names, whether hierarchy is expressed
by storage position or reference, how conventions are stored and discovered, how
agents obtain data, how new areas are opened, any validation mechanism, any
license instrument, and any agent tool surface.

### Three caveats on the strength of the evidence

1. **The convergence map was not built cold.** The method calls for building it
   before reading the project. This project had already been read in the same
   session, during `discover-intent` and `intent-alignment`. The dimensions below
   were drawn from what the three designers addressed, but the independence is
   weaker than a cold run would give.
2. **Convergence on git and YAML should be discounted.** All three chose both,
   and all three marked both arbitrary. Three language models agreeing on YAML is
   more likely a shared prior than a property of this intent.
3. **`INTENT.md` was revised after this run.** The brief was built from the
   intent as it stood before full autonomy became the stated goal. The revision
   does not invalidate the findings — see the closing section — but the criterion
   numbers cited here are the pre-revision ones.

## The convergence map

**Forced** — all three independently landed in materially the same place:

| Dimension | What all three did |
|-----------|--------------------|
| Proposal and review state | Committed into the repository, not left in forge metadata — all three reasoned that governance must survive a forge migration |
| Hierarchy primitive | A single recursive grouping; a "kind of collectible" is just a root grouping. All three marked the collapse arbitrary and all three did it |
| Hierarchy expression | Explicit parent reference, not storage position |
| Identity | Opaque, coordination-free identifiers, decoupled from a mutable slug, referenced by ID and never by path |
| Retirement | Tombstones, never deletion — all three derived this from "every reference resolves" |
| Fact provenance | Per-claim `{field, value, source}` as discrete, individually checkable units |
| Convention record | Every grouping carries membership, naming, completeness, and authoritative sources, inheritable from its parent |
| Storage layout | One file per entity in a directory tree. All three explicitly rejected the single-file, line-delimited, and embedded-database options the brief offered, for the same reason: diff granularity must match review granularity |
| Role of position | Slugs are decorative; the identifier is the authority |
| Validation gate | A mechanical pre-merge check: identifier uniqueness, references resolve, convention present, image host present |
| Validation vs. verification | Structural soundness and factual soundness are separate gates; neither substitutes for the other |
| Verifier identity | The verifier must differ from the proposer, mechanically enforced |
| Merge policy | Two tiers — routine verified changes merge automatically; anything establishing conventions, or arriving from outside, is human-gated |
| Opening a new area | The agent drafts the conventions; the human ratifies rather than authors |
| Derived index | A generated identifier-to-location map, explicitly non-authoritative |
| Consumer surface | The repository is the interface, plus a generated flat export as a convenience derivative |

**Arbitrary** — the three scattered, so the intent does not reach these. No
finding follows from the current design's choice in any of them: source as a
standalone entity versus an inline field, the variant and relation mechanism,
per-grouping schema extensions, and single-parent versus multi-parent hierarchy.

## Validated

Nine forced choices that the current design already matches. Three designers who
could not see this project rebuilt them from its purpose alone, which means they
are entailed by what the project is for rather than accidents of history:

- Stable UUIDs, generated once and never reused, referenced by identifier and
  never by path
- One file per entity, plain text, in a directory tree
- A convention record per category, resolved by walking up the tree
- A mechanical pre-merge validation gate enforcing referential integrity and
  convention presence
- Structural validation separated from factual verification
- An independent verifier distinct from the proposer
- Two-tier merge: routine changes automatic, conventions and outside
  contributions gated
- Rejected proposals retained rather than discarded
- Images recorded by reference, never copied

## Divergences

| # | Divergence | Steelman | Verdict |
|---|------------|----------|---------|
| 1 | An agent cannot author a category's conventions — `upsertCollection` refuses by construction | The concern is real: an agent that writes its own rules and then follows them is marking its own homework | **Greenfield wins.** All three preserved human authority by separating *draft* from *ratify*. The current design conflates "the human decides" with "the human writes" |
| 2 | No per-claim provenance; only `image.source_url` exists | The metadata non-goal pushes against field depth, and category-level authoritative sources already exist — which is the half all three designs also required | **Greenfield wins.** Note the derivation: all three reached per-claim provenance from the *verification* criterion, not the *attribution* one. It survives the Criterion 5 rewrite because it never depended on it |
| 3 | Verification state lives in pull-request comments | `lib/ledger.mjs` documents precisely why a committed record was rejected: a constantly-rewritten shared file conflicts across concurrent audit PRs and jams the review cron | **Greenfield wins, narrowly.** The documented failure was a *single shared rolling file*. A per-proposal record at a unique path cannot collide, so the objection does not reach the greenfield shape |
| 4 | Hierarchy derives from directory position; the validator rejects an explicit parent field | `docs/primitives/COMPONENT.md` defends this well — exactly one directory anywhere asserts a given truth, no sibling tree to keep in sync, and `git mv` re-parents atomically. Cross-cutting membership is already handled by tags | **Open.** Both are coherent. Position-as-parentage is safe here precisely because nothing references anything by path |
| 5 | No tombstone or retirement mechanism | CI blocks any deletion that would dangle a reference — a different solution to the same problem, and a simpler one | **Open.** Equivalent inside the repository. Tombstones additionally serve an external consumer who cached an identifier, which CI cannot |
| 6 | No derived index and no consumer export | None found | **Greenfield wins** — already tracked as `ALIGNMENT.md` remediation item 3 |

## Migration

Only Greenfield-wins items are eligible. Item 6 belongs to the alignment plan and
is not duplicated here.

1. **Separate drafting from ratifying.** The alignment plan proposed a
   `scaffold_category` template generator; all three designs go further — the
   agent authors the substance of membership, naming, completeness, and sources,
   bundled with seed data into a single proposal that is always human-gated.
   Sequencing stays with the alignment plan, which already holds this as item 1.

2. **Per-claim provenance on new entries.** Add `{field, value, source}`
   alongside existing bare fields, forward-only, with no backfill of the existing
   corpus. This is what turns re-verification from a judgment about a whole diff
   into a checklist over discrete claims.

3. **Commit the verification record.** One file per proposal, at a unique path,
   merged alongside the change it verifies. Avoids the conflict the audit ledger
   warned about, and makes review history survive a forge migration.

None of these can be crossed in a single step, and none requires a rewrite — each
is incremental and leaves the project working throughout.

## What this exposed about the intent

All three designers independently identified the same internal inconsistency:
the Purpose stated that a human reviews every addition, while the Non-Goals
permitted automatic merge of the project's own agent-generated changes as a
narrow exception. Read literally, those conflicted. All three resolved it the
same way — "reviewed" is satisfied by independent per-claim verification, with
the human gate reserved for conventions and outside contributions — and all three
flagged their resolution as an interpretation rather than a derivation.

That tension has since been resolved in `INTENT.md`, in the direction of full
autonomy: verification is now the sole gate, applied uniformly regardless of who
proposed a change, and human review is opt-in per collection.

**The revision strengthens every finding above rather than weakening it.** Under
the previous intent, the three migration items were improvements. Under full
autonomy they are load-bearing: per-claim provenance and committed verification
records are what make a uniform verification gate enforceable at all, and
agent-authored conventions are what make an autonomous catalog possible. The
designers built the machinery that full autonomy requires before full autonomy
was the stated goal.
