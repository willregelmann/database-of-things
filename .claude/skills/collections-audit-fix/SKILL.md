---
name: collections-audit-fix
description: Autonomous single-pass audit-and-fix of one randomly-chosen collection using the collections-mcp tools, opening a PR via the deterministic submit.mjs pipeline if anything changed. This is what the scheduled hourly job runs. For a read-only, human-directed audit with no auto-fixing, use collections-audit instead.
---

# Collections Audit + Fix (autonomous)

One pass, one randomly-chosen collection, may write — but only through the
`collections-mcp` MCP tools, never by editing `collections/**` directly.
That tool surface is deliberately narrow: `upsert_item`/`upsert_collection`
can only patch field values or add a new item/nested collection record,
`upsert_component` does the same for a collection's components bucket (e.g.
a LEGO theme's minifigures — see collections/CLAUDE.md, "Components"), and
`rename_item` can rename a single item's file in place (same directory
only) — nothing beyond that. No moving items between collections, no
renaming/restructuring a whole collection directory, no bootstrapping a
brand-new components bucket, no authoring a new `CLAUDE.md` or
`template.schema.json`. Anything a finding needs beyond that: call
`flag_finding` instead — don't just mention it in your final report and
leave it there, that's easy to miss and gets forgotten. `flag_finding`
becomes a real GitHub issue after your session ends; text you only say in
your final report doesn't durably go anywhere.

This exists for the scheduled hourly job. For a manual, read-only audit
(no writes, for when a human wants a report to review before touching
anything), use the `collections-audit` skill instead — same three audit
dimensions, just without the fix step.

## Hard rules

- **Only touch `collections/**` through the `collections-mcp` tools.** You
  don't have Read/Write/Edit/Bash access in this job at all — the narrow
  MCP tool surface is the entire interface, enforced by the invocation
  itself, not just by this instruction.
- **You never run `git`/`gh`/`submit.mjs` — that happens after you're done,
  outside this session.** The wrapper that invoked you runs
  `node tools/collections-mcp/submit.mjs` once you finish (deterministic:
  re-validates, builds the branch/commit/PR body mechanically from the
  changelog, no free-form summary). Your only job is auditing and, where
  warranted, calling `upsert_item`/`upsert_collection` — nothing about
  submission is yours to decide or trigger.
- **Cite a source for every fix.** Don't fabricate something you can't
  verify — leave it unfixed. If it's a real gap, the same collection (or a
  sibling) will come up again on a future random pick; if you can't verify
  it, an unconfirmed guess is worse than a gap.
- **One level only.** Same scope as `collections-audit` — don't recurse into
  a nested collection you didn't land on; that's a separate future
  invocation's job.
- **Field-value fixes and single-item renames only.** No moving items
  between collections, no renaming a whole collection directory, no
  authoring new curation conventions — the tools don't expose any of
  that, so it's enforced by construction, not just policy.
- **A rename is still a fix, not an excuse to skip verification.** A prior
  run once flagged two "inconsistently named" files by pattern-matching
  against a sibling reprint pair, without checking whether the two cards
  actually shared a name the way that sibling pair did — they didn't (they
  were genuinely different cards whose numbers are part of the real
  name), so the "fix" would have broken correct data. Verify a rename
  target the same way you'd verify any other fact before calling
  `rename_item`.

## Steps

1. `choose_random_collection()` → the target for this run.
2. `get_collection_context(collection_id)` → read the full applicable
   `CLAUDE.md` chain (root → domain family → category → any intermediate →
   own) and resolved `template.schema.json` before doing anything else.
3. `get_collection_details(collection_id)` and, depending on what this
   collection actually contains, `list_items(collection_id)` and/or
   `list_collections(collection_id)` → orient on what's here.
   `get_collection_details`'s `componentBuckets` field lists any components
   buckets this collection has (e.g. `["minifigs"]`) — use
   `list_components(collection_id, bucket)` to see what's in one.
4. Audit the same three dimensions `collections-audit` does, using these
   tools for reads instead of raw files, and web search for verification:
   - **Conformance** — does this collection follow the CLAUDE.md chain from
     step 2 (naming, dates, tags, logos, collection shape, category-specific
     pitfalls)?
   - **Own-record accuracy** — is `get_collection_details`'s data (name,
     date, description, image) correct and complete per an authoritative
     source?
   - **Content completeness/accuracy** — are this collection's *direct*
     children (via `list_items`/`list_collections`, drilling into
     `get_item_details` as needed) complete and correct per an authoritative
     source? Spot-check rather than exhaustively re-verify *existing*
     items in a large collection — but if you find a genuine, well-sourced
     **completeness** gap (missing items, not just a wrong field), populate
     the whole gap, not just one token entry. A PR is reviewed before it
     merges either way, so a large well-sourced batch costs the same as a
     small one if you're right, and is just as cheap to reject if you're
     not — restraint here isn't protecting anything. Every individual item
     in the batch still needs the same per-item sourcing rigor as a
     one-off fix; "there are many of them" is never a reason to skip
     verifying one.
5. For each finding that's well-sourced:
   - **Fixable within the tool surface** (a wrong/missing field value, a
     missing item, a missing component in an existing bucket, a missing
     nested collection record, or a single item's file misnamed relative to
     its own correct content): call
     `upsert_item`/`upsert_component`/`upsert_collection`/`rename_item` as
     appropriate.
   - **Not fixable within the tool surface** (moving an item between
     collections, restructuring a whole collection directory, bootstrapping
     a brand-new components bucket, a missing sibling collection outside
     this one's scope, or genuine human judgment): call `flag_finding` with
     a specific title and a body that includes your source(s) and why the
     other tools can't handle it.
     Only flag things you're confident are real and well-sourced — same
     discipline as a fix, just a different outcome.
   - Anything you can't confirm one way or the other: leave it alone
     entirely. Don't fix, don't flag, don't guess.
6. When you're done, just report back: which collection you audited, what
   (if anything) you changed, and what (if anything) you flagged. Don't try
   to submit or file anything yourself — the wrapper handles both the PR
   and any issues after your session ends.
