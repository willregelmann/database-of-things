import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { REPO_ROOT } from './lib/repo.mjs';
import { readAll, clear } from './lib/changelog.mjs';

// Deterministic post-session pipeline: no LLM judgment involved past this
// point. The PR title/body (for upserts) and issue title/body (for flagged
// findings) are generated mechanically from the changelog — the same set
// of entries always produces the same output.

const DRY_RUN = process.argv.includes('--dry-run');
const FLAG_LABEL = 'audit-finding';

function git(args) {
  return execFileSync('git', args, { cwd: REPO_ROOT, encoding: 'utf8' }).trim();
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
  const label = entry.kind === 'item' ? 'item' : 'collection';
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

function buildPr(changes) {
  const created = changes.filter((e) => e.action === 'create').length;
  const updated = changes.filter((e) => e.action === 'update').length;
  const renamed = changes.filter((e) => e.kind === 'rename').length;
  const parts = [];
  if (created) parts.push(`${created} added`);
  if (updated) parts.push(`${updated} updated`);
  if (renamed) parts.push(`${renamed} renamed`);
  const title = `Audit fixes: ${parts.join(', ')}`;
  const body = [
    'Automated audit of a randomly-selected collection.',
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
    `_Collection: \`${flag.collectionPath}\` (id \`${flag.collectionId}\`). Filed automatically by the collections-audit-fix job — the collections-mcp tool surface (upsert_item/upsert_collection/rename_item) couldn't cover this one._`,
  ].join('\n');
  return { title: flag.title, body };
}

const entries = readAll();
const changes = entries.filter((e) => e.kind === 'item' || e.kind === 'collection' || e.kind === 'rename');
const flags = entries.filter((e) => e.kind === 'flag');

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
  const originalBranch = git(['rev-parse', '--abbrev-ref', 'HEAD']);

  console.log(`\n--- ${DRY_RUN ? 'DRY RUN — would run' : 'submitting PR'} ---`);
  console.log(`branch: ${branch}`);
  console.log(`files: ${paths.join(', ')}`);
  console.log(`title: ${title}`);
  console.log(`body:\n${body}`);

  if (!DRY_RUN) {
    git(['checkout', '-b', branch]);
    git(['add', ...paths]);
    git(['commit', '-m', `${title}\n\n${body}`]);
    git(['push', '-u', 'origin', branch]);
    const prUrl = execFileSync('gh', ['pr', 'create', '--title', title, '--body', body, '--head', branch], {
      cwd: REPO_ROOT,
      encoding: 'utf8',
    }).trim();
    git(['checkout', originalBranch]);
    console.log(`\nopened: ${prUrl}`);
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
      ['issue', 'create', '--title', title, '--body', body, '--label', FLAG_LABEL],
      { cwd: REPO_ROOT, encoding: 'utf8' }
    ).trim();
    console.log(`opened: ${issueUrl}`);
  }
}

if (!DRY_RUN) {
  clear();
}
