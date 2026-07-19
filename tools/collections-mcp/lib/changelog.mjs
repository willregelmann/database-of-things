import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './repo.mjs';

// One changelog file per running server process (a session audits exactly
// one collection). Never committed — submit.mjs reads it to build the PR,
// then deletes it; it's gitignored so a crashed run can't leak into a diff.
const CHANGELOG_PATH =
  process.env.COLLECTIONS_MCP_CHANGELOG || path.join(REPO_ROOT, 'tools', 'collections-mcp', '.changelog.json');

export function appendEntry(entry) {
  const entries = readAll();
  entries.push({ timestamp: new Date().toISOString(), ...entry });
  fs.writeFileSync(CHANGELOG_PATH, JSON.stringify(entries, null, 2));
}

export function readAll() {
  if (!fs.existsSync(CHANGELOG_PATH)) return [];
  return JSON.parse(fs.readFileSync(CHANGELOG_PATH, 'utf8'));
}

export function clear() {
  if (fs.existsSync(CHANGELOG_PATH)) fs.unlinkSync(CHANGELOG_PATH);
}

export function changelogPath() {
  return CHANGELOG_PATH;
}
