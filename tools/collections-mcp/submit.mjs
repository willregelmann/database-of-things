import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { REPO_ROOT } from './lib/repo.mjs';
import { readAll, clear } from './lib/changelog.mjs';

// Deterministic post-session pipeline: no LLM judgment involved past this
// point. The PR title/body are generated mechanically from the changelog —
// same set of upserts always produces the same PR content.

const DRY_RUN = process.argv.includes('--dry-run');

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
  const label = entry.kind === 'item' ? 'item' : 'collection';
  if (entry.action === 'create') {
    return `- Added ${label} **${entry.after.name}** (\`${entry.id}\`) at \`${entry.path}\``;
  }
  const diffs = diffFields(entry.before, entry.after);
  const fieldList = diffs.map((d) => `\`${d.field}\`: ${JSON.stringify(d.from)} → ${JSON.stringify(d.to)}`).join(', ');
  return `- Updated ${label} **${entry.after.name}** (\`${entry.id}\`) at \`${entry.path}\` — ${fieldList || 'no field diff'}`;
}

function buildMessage(entries) {
  const created = entries.filter((e) => e.action === 'create').length;
  const updated = entries.filter((e) => e.action === 'update').length;
  const parts = [];
  if (created) parts.push(`${created} added`);
  if (updated) parts.push(`${updated} updated`);
  const title = `Audit fixes: ${parts.join(', ')}`;
  const body = [
    'Automated audit of a randomly-selected collection.',
    '',
    ...entries.map(formatEntry),
    '',
    '_Generated mechanically from the collections-mcp changelog — no free-form summary._',
  ].join('\n');
  return { title, body };
}

const entries = readAll();
if (entries.length === 0) {
  console.log('no changelog entries — nothing to submit');
  process.exit(0);
}

const validateOutput = execFileSync('node', ['validate.mjs'], {
  cwd: `${REPO_ROOT}/tools/collections-validate`,
  encoding: 'utf8',
}); // throws on non-zero exit, which is what we want: abort, don't touch git
console.log(validateOutput.trim());

const paths = [...new Set(entries.map((e) => e.path))];
const { title, body } = buildMessage(entries);
const branch = `audit/${crypto.randomUUID().slice(0, 8)}`;
const originalBranch = git(['rev-parse', '--abbrev-ref', 'HEAD']);

console.log(`\n--- ${DRY_RUN ? 'DRY RUN — would run' : 'submitting'} ---`);
console.log(`branch: ${branch}`);
console.log(`files: ${paths.join(', ')}`);
console.log(`title: ${title}`);
console.log(`body:\n${body}`);

if (DRY_RUN) {
  process.exit(0);
}

git(['checkout', '-b', branch]);
git(['add', ...paths]);
git(['commit', '-m', `${title}\n\n${body}`]);
git(['push', '-u', 'origin', branch]);
const prUrl = execFileSync('gh', ['pr', 'create', '--title', title, '--body', body, '--head', branch], {
  cwd: REPO_ROOT,
  encoding: 'utf8',
}).trim();
git(['checkout', originalBranch]);
clear();

console.log(`\nopened: ${prUrl}`);
