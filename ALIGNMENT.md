*Point-in-time snapshot, 2026-07-25. Measures the project against `INTENT.md`
as it stood on that date. Expected to go stale — re-run `intent-alignment`
rather than editing this file.*

## Assessment

The disciplines are in excellent shape and the ambitions are early. Everything
the project promised *not* to do, it isn't doing — all seven non-goals
respected, including the hard one of keeping a live downstream consumer from
shaping the schema. The correctness machinery is real: the validator passes
clean across 26,579 entities and CI gates every pull request. What is unmet is
breadth, and the reason is a single structural blocker that most other progress
waits behind.

## Purpose

**Partially met.** The governance half holds completely: no write path exists
outside a pull request, the validator runs on every PR, and the catalog carries
no consumer-specific fields. The ambition half is early. "A human reviewing
rather than authoring every addition" holds for items but not for categories —
every category's conventions are hand-written.

## Users

| User | Verdict | Evidence |
|------|---------|----------|
| Data consumers | Partially met | Stable UUIDs enforced across 26,579 entities; CC0 requires no permission. No release tag, no dump, no index — enumeration means cloning and walking 26,119 files |
| Curating agents | Met | Validator hard-enforces `CLAUDE.md` + schema reachability for every entity-holding directory (`validate.mjs:116,119`); hourly loop produces merged work |
| Maintainer-curator | Met | Sole category authority; the review job takes the first pass. 6 open PRs, 11 open issues — a working queue, not a stall |
| Prospective contributors | Partially met | The PR path works and CI gates it. Nothing else exists — no `CONTRIBUTING.md`, no issue templates, no outside contributor across 408 commits (393 maintainer, 15 dependabot) |

## Success Criteria

| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | Breadth over concentration | Unmet — attempted, not reached | Trading card games 20,678 of 26,119 items (79%); plush 3,258; figures 2,090; comics 76; manga 12; model kits 5; video games 0. Work is going elsewhere — PR #193 adds 141 Game Boy items — but three orders of magnitude separate top from bottom |
| 2 | Agent can open a new category | Unmet — structurally blocked | `upsertCollection` never authors `CLAUDE.md`/`template.schema.json` (`lib/mutate.mjs:234-238`); `upsertComponent` the same for buckets. The blocker is deliberate, not incidental |
| 3 | Agent changes independently re-verified | Contested — see below | 53 merged `audit-finding` PRs. 22 carry no review evidence, all merged 2026-07-19 → 07-22. The review job landed 07-22. 31 of 31 merges after that date carry it |
| 4 | Every entity resolves | Met | Validator clean: 26,579 entities, no duplicate identifiers, no dangling tag or component references, no collection directory missing its record. Tag coverage 23,510/26,119 (90%) — informational, not an error |
| 5 | Source attribution | Partially met | Assessed against the pre-revision wording. `image.source_url` present on 22,777 of 26,119 items (87%). No schema anywhere defined a source field for non-image facts — a card's date, rarity, and illustrator had nowhere to record provenance. The criterion was rewritten this run; the new wording applies from the next assessment |
| 6 | Category is self-explaining | Partially met | Belonging and naming are enforced and pass. Completeness is not: 17 of 44 `CLAUDE.md` files mention it |

**Criterion 3 turns on a reading.** Graded against the gate, it is **Met** — the
review job has held on every merge since it landed. Graded against the corpus
as the criterion is literally written ("every merged agent-authored change"), it
is **Partially met**: 22 changes merged without re-verification and their data
is in the catalog now. The gate is sound going forward; the corpus has a hole.
Unresolved as of this snapshot.

## Non-Goals

| Non-goal | Verdict | Evidence |
|----------|---------|----------|
| Exhaustive metadata | Respected | Largest schema has 7 properties; most carry 3–5 |
| Market or pricing data | Respected | Zero price or value fields across 393 collections |
| Hosting or redistributing images | Respected | 0 image files tracked in the repository |
| Being authoritative | Respected | `DISCLAIMER.md` states the data is offered as-is; nothing claims authority |
| Serving one downstream application | Respected | 0 consumer-specific fields in any schema, despite a live downstream consumer |
| Completion tracking as a purpose | Respected | No completion or progress machinery in any tool |
| Automatic merge of outside contributions | Respected | Merge authority scoped to the `audit-finding` label and `audit/<hash>` branches. Note: that scope is enforced by instruction, not by branch protection |

## Remediation

Priority order. Each item names the smallest change that would move the verdict.

1. **Unblock category creation.** Convention-authoring sits outside the tool
   surface, so agents can only fill categories a human has opened. Add a
   `scaffold_category` operation that writes `CLAUDE.md` and
   `template.schema.json` from a template and opens a *conventions* PR,
   separate from data PRs — the human still decides, but stops hand-authoring.
   Moves Criterion 2 from structurally blocked to attempted. This is the lever
   on breadth; pushing directly on Criterion 1 while opening a category remains
   hand-work is the wrong move.

2. **Write completeness guidance.** 27 of 44 `CLAUDE.md` files do not say how to
   tell when a collection is finished. Add a completeness section, largest
   collections first (squishmallows, 2,321 items). Moves Criterion 6 to met.
   May also bear on the audit loop's no-change rate: a loop with no definition
   of "complete" has no way to stop re-auditing finished collections.

3. **Publish a consumable artifact.** CC0 data that requires cloning and walking
   26,119 YAML files is reusable in principle only. A CI job publishing a JSON
   dump or tagged release on merge to main moves Data consumers to met.

4. **Harden the audit merge scope.** The job's authority is a prompt rule. A CI
   check refusing merges from branches outside `audit/*` under the job's token
   makes it mechanical, protecting a non-goal that is currently respected only
   by instruction.

5. **Contributor scaffolding.** Contingent — Open Question 3 asks whether
   outside contribution is a goal at all. Decide before writing
   `CONTRIBUTING.md`.

No action needed on Criterion 4, which is met and continuously enforced.

## Unresolved

- **Criterion 3's reading** — gate or corpus. Determines whether backfilling
  re-verification of the 22 pre-gate PRs is required work.
- **Purpose vs. Criterion 2** — the Purpose now states that a category is
  scaffolded with its conventions before anything is catalogued in it, while
  Criterion 2 targets removing the human from that step. Worded as sequencing
  rather than as a division of labor so both can stand; if the human half is
  meant to be permanent, Criterion 2 should be dropped instead.

## Changes made to INTENT.md this run

- Criterion 5 rewritten: the original claimed every non-obvious fact traces to a
  recorded source, describing a mechanism that has never existed. Now states
  image attribution plus category-named authoritative sources.
- Open Question 3 closed as settled. `video-games/nintendo/game-boy` was
  scaffolded by hand with conventions, left empty, and PR #193 has the audit
  loop adding 141 items to it — scaffolding demonstrably functions as a to-do
  list the loop picks up. The scaffold-then-fill division was promoted into the
  Purpose.
