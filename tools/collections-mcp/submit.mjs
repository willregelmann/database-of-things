import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { REPO_ROOT, COLLECTIONS_ROOT, buildIndex, getCollection } from './lib/repo.mjs';
import { readAll, clear } from './lib/changelog.mjs';

// Deterministic post-session pipeline: no LLM judgment involved past this
// point. The PR title/body (for upserts) and issue title/body (for flagged
// findings) are generated mechanically from the changelog — the same set
// of entries always produces the same output.

const DRY_RUN = process.argv.includes('--dry-run');
const AUDIT_LABEL = 'audit-finding';

function git(args) {
  return execFileSync('git', args, { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
}

// `--abbrev-ref HEAD` prints the literal string "HEAD" when detached
// (which the dedicated audit checkout always is between ticks). Checking
// that string back out later would just re-resolve to whatever HEAD
// happens to point to *at that moment* -- not the commit we started from,
// since by then HEAD has moved to the tip of the throwaway branch below.
// Capture the concrete SHA whenever detached so the `finally` restore is a
// real snapshot; stay branch-based when on a real branch (manual/CLI use)
// so that case still lands back on the branch itself, not a detached SHA.
function currentRef() {
  const ref = git(['rev-parse', '--abbrev-ref', 'HEAD']);
  return ref === 'HEAD' ? git(['rev-parse', 'HEAD']) : ref;
}

function diffFields(before, after) {
  const changed = [];
  const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})]);
  for (const key of keys) {
    if (key === 'id') continue;
    const a = JSON.stringify(before ? before[key] : undefined);
    const b = JSON.stringify(after ? after[key] : undefined);
    if (a !== b) changed.push({ field: key, from: before ? before[key] : undefined, to: after ? after[key] : undefined });
  }
  return changed;
}

function formatEntry(entry) {
  if (entry.kind === 'rename') {
    return `- Renamed ${entry.entityKind} at \`${entry.oldPath}\` to \`${entry.newPath}\``;
  }
  const label = entry.kind === 'item' ? 'item' : entry.kind === 'component' ? 'component' : 'collection';
  if (entry.action === 'create') {
    return `- Added ${label} **${entry.after.name}** (\`${entry.id}\`) at \`${entry.path}\``;
  }
  const diffs = diffFields(entry.before, entry.after);
  const fieldList = diffs.map((d) => `\`${d.field}\`: ${JSON.stringify(d.from)} → ${JSON.stringify(d.to)}`).join(', ');
  return `- Updated ${label} **${entry.after.name}** (\`${entry.id}\`) at \`${entry.path}\` — ${fieldList || 'no field diff'}`;
}

function entryPaths(entry) {
  return entry.kind === 'rename' ? [entry.oldPath, entry.newPath] : [entry.path];
}

// The collectionId recorded on a changelog entry is whichever collection
// the write actually landed in/under, and every entry in a run traces back
// to the one collection that run's session audited (single-collection,
// one-level-only per the skill) — so the first entry that has one names it
// for the whole run. Resolved from the on-disk index (not the changelog
// entry itself) so we always show the collection's current path, not a
// stale one recorded before an audit-time rename elsewhere in the run.
function resolveCollectionLabel(changes) {
  const collectionId = changes.map((e) => e.collectionId).find(Boolean);
  if (!collectionId) return null;
  try {
    const node = getCollection(buildIndex(), collectionId);
    return path.relative(COLLECTIONS_ROOT, node.dir);
  } catch {
    return null;
  }
}

function buildPr(changes) {
  const created = changes.filter((e) => e.action === 'create').length;
  const updated = changes.filter((e) => e.action === 'update').length;
  const renamed = changes.filter((e) => e.kind === 'rename').length;
  const parts = [];
  if (created) parts.push(`${created} added`);
  if (updated) parts.push(`${updated} updated`);
  if (renamed) parts.push(`${renamed} renamed`);
  const label = resolveCollectionLabel(changes);
  const title = label ? `Audit fixes (${label}): ${parts.join(', ')}` : `Audit fixes: ${parts.join(', ')}`;
  const body = [
    label ? `Automated audit of \`${label}\`.` : 'Automated audit of a randomly-selected collection.',
    '',
    ...changes.map(formatEntry),
    '',
    '_Generated mechanically from the collections-mcp changelog — no free-form summary._',
  ].join('\n');
  return { title, body };
}

function buildIssue(flag) {
  const body = [
    flag.body,
    '',
    `_Collection: \`${flag.collectionPath}\` (id \`${flag.collectionId}\`). Filed automatically by the collections-audit-fix job — the collections-mcp tool surface (upsert_item/upsert_component/upsert_collection/rename_item) couldn't cover this one._`,
  ].join('\n');
  return { title: flag.title, body };
}

// The one path that must still exist on disk for this entry to be
// legitimately submittable. A create/update's `path` or a rename's
// `newPath` going missing means something deleted the file out-of-band
// after the changelog entry was written (e.g. a stale scratch-test
// leftover) -- stale entries like that must never take the whole batch
// down with them.
function survivingPath(entry) {
  return entry.kind === 'rename' ? entry.newPath : entry.path;
}

const entries = readAll();
const rawChanges = entries.filter((e) => e.kind === 'item' || e.kind === 'component' || e.kind === 'collection' || e.kind === 'rename');
const flags = entries.filter((e) => e.kind === 'flag');

const changes = rawChanges.filter((e) => fs.existsSync(path.join(REPO_ROOT, survivingPath(e))));
const stale = rawChanges.filter((e) => !fs.existsSync(path.join(REPO_ROOT, survivingPath(e))));
for (const e of stale) {
  console.log(`skipping stale changelog entry (path no longer exists): ${survivingPath(e)}`);
}

if (entries.length === 0) {
  console.log('no changelog entries — nothing to submit');
  process.exit(0);
}

if (changes.length > 0) {
  const validateOutput = execFileSync('node', ['validate.mjs'], {
    cwd: `${REPO_ROOT}/tools/collections-validate`,
    encoding: 'utf8',
  }); // throws on non-zero exit, which is what we want: abort, don't touch git
  console.log(validateOutput.trim());

  const paths = [...new Set(changes.flatMap(entryPaths))];
  const { title, body } = buildPr(changes);
  const branch = `audit/${crypto.randomUUID().slice(0, 8)}`;
  const originalBranch = currentRef();

  console.log(`\n--- ${DRY_RUN ? 'DRY RUN — would run' : 'submitting PR'} ---`);
  console.log(`branch: ${branch}`);
  console.log(`files: ${paths.join(', ')}`);
  console.log(`title: ${title}`);
  console.log(`body:\n${body}`);

  if (!DRY_RUN) {
    try {
      git(['checkout', '-b', branch]);
      git(['add', ...paths]);
      git(['commit', '-m', `${title}\n\n${body}`]);
      git(['push', '-u', 'origin', branch]);
      const prUrl = execFileSync('gh', ['pr', 'create', '--title', title, '--body', body, '--head', branch, '--label', AUDIT_LABEL], {
        cwd: REPO_ROOT,
        encoding: 'utf8',
      }).trim();
      console.log(`\nopened: ${prUrl}`);
    } finally {
      // Always get back to where we started, whatever failed and
      // wherever it failed -- a half-finished PR attempt must never
      // strand the working tree on a throwaway branch.
      git(['checkout', originalBranch]);
    }
  }
}

for (const flag of flags) {
  const { title, body } = buildIssue(flag);
  console.log(`\n--- ${DRY_RUN ? 'DRY RUN — would file issue' : 'filing issue'} ---`);
  console.log(`title: ${title}`);
  console.log(`body:\n${body}`);

  if (!DRY_RUN) {
    const issueUrl = execFileSync(
      'gh',
      ['issue', 'create', '--title', title, '--body', body, '--label', AUDIT_LABEL],
      { cwd: REPO_ROOT, encoding: 'utf8' }
    ).trim();
    console.log(`opened: ${issueUrl}`);
  }
}

if (!DRY_RUN) {
  clear();
}
