---
name: collections-audit-fix
description: Autonomous single-pass audit-and-fix of one randomly-chosen collection using the collections-mcp tools, opening a PR via the deterministic submit.mjs pipeline if anything changed. This is what the scheduled hourly job runs. For a read-only, human-directed audit with no auto-fixing, use collections-audit instead.
---

# Collections Audit + Fix (autonomous)

One pass, one randomly-chosen collection, may write — but only through the
`collections-mcp` MCP tools, never by editing `collections/**` directly.
That tool surface is deliberately narrow: `upsert_item`/`upsert_collection`
can only patch field values or add a new item/nested collection record —
never rename/move a file, never author a new `CLAUDE.md` or
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
- **Field-value fixes only.** No renames, no restructuring — the tools
  don't expose that, so this is enforced by construction, not just policy.

## Steps

1. `choose_random_collection()` → the target for this run.
2. `get_collection_context(collection_id)` → read the full applicable
   `CLAUDE.md` chain (root → domain family → category → any intermediate →
   own) and resolved `template.schema.json` before doing anything else.
3. `get_collection_details(collection_id)` and, depending on what this
   collection actually contains, `list_items(collection_id)` and/or
   `list_collections(collection_id)` → orient on what's here.
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
     source? Spot-check rather than exhaustively re-verify a large
     collection.
5. For each finding that's well-sourced:
   - **Fixable within the tool surface** (a wrong/missing field value, a
     missing item, a missing nested collection record): call
     `upsert_item`/`upsert_collection`.
   - **Not fixable within the tool surface** (needs a rename/restructure, a
     missing sibling collection outside this one's scope, or genuine
     human judgment): call `flag_finding` with a specific title and a body
     that includes your source(s) and why the upsert tools can't handle
     it. Only flag things you're confident are real and well-sourced —
     same discipline as a fix, just a different outcome.
   - Anything you can't confirm one way or the other: leave it alone
     entirely. Don't fix, don't flag, don't guess.
6. When you're done, just report back: which collection you audited, what
   (if anything) you changed, and what (if anything) you flagged. Don't try
   to submit or file anything yourself — the wrapper handles both the PR
   and any issues after your session ends.
