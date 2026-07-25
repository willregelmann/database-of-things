#!/usr/bin/env node
// Reads the audit ledger (see lib/ledger.mjs) and answers the questions that
// were unanswerable before it existed. Read-only; run it whenever, or after a
// few weeks of ticks to settle a scheduling argument with data.
//
//   node tools/collections-mcp/ledger-report.mjs
//   node tools/collections-mcp/ledger-report.mjs --unpicked   # full list
import path from 'node:path';
import { readAll, ledgerPath } from './lib/ledger.mjs';
import { buildIndex, getCollection, COLLECTIONS_ROOT } from './lib/repo.mjs';

const SHOW_ALL_UNPICKED = process.argv.includes('--unpicked');
const entries = readAll();

if (entries.length === 0) {
  console.log(`no ledger entries yet at ${ledgerPath()}`);
  console.log('(the ledger is local to whichever checkout runs the job — it starts empty)');
  process.exit(0);
}

const picks = entries.filter((e) => e.event === 'pick');
const outcomes = entries.filter((e) => e.event === 'outcome' && !e.dry_run);
const span = [entries[0].ts, entries[entries.length - 1].ts];

console.log(`ledger: ${ledgerPath()}`);
console.log(`${entries.length} entries — ${picks.length} picks, ${outcomes.length} outcomes`);
console.log(`window: ${span[0]} → ${span[1]}\n`);

// --- outcome mix: the correctness-vs-growth split, measured ---------------
const byResult = new Map();
for (const o of outcomes) byResult.set(o.result, (byResult.get(o.result) || 0) + 1);
console.log('outcomes:');
for (const [r, n] of [...byResult].sort((a, b) => b[1] - a[1])) {
  console.log(`  ${String(n).padStart(5)}  ${String(((100 * n) / outcomes.length).toFixed(1)).padStart(5)}%  ${r}`);
}
const yielded = outcomes.filter((o) => o.result !== 'none').length;
console.log(`  ${'—'.repeat(30)}`);
console.log(`  yield rate: ${((100 * yielded) / (outcomes.length || 1)).toFixed(1)}% of runs produced a PR or issue\n`);

// A pick with no matching outcome means the run died between the two.
const orphanPicks = picks.length - outcomes.length;
if (orphanPicks > 0) {
  console.log(`⚠ ${orphanPicks} pick(s) with no recorded outcome — sessions that died before submit.mjs ran\n`);
}

// --- revisit behaviour: is uniform sampling actually revisiting? ----------
const timesPicked = new Map();
for (const p of picks) {
  if (!p.collection_id) continue;
  timesPicked.set(p.collection_id, (timesPicked.get(p.collection_id) || 0) + 1);
}
const repeats = [...timesPicked.values()].filter((n) => n > 1).length;
console.log(`revisits: ${timesPicked.size} distinct collections picked, ${repeats} picked more than once`);
if (repeats > 0) {
  const byPath = new Map();
  for (const p of picks) if (p.path) byPath.set(p.path, (byPath.get(p.path) || 0) + 1);
  for (const [p, n] of [...byPath].filter(([, n]) => n > 1).sort((a, b) => b[1] - a[1]).slice(0, 10)) {
    console.log(`  ${String(n).padStart(3)}x  ${p}`);
  }
}

// --- coverage: what has the sampler never looked at? ---------------------
let pool = [];
try {
  const index = buildIndex();
  pool = index.collectionIds;
} catch {
  console.log('\n(could not build the collection index — skipping coverage)');
}
if (pool.length) {
  const unpicked = pool.filter((id) => !timesPicked.has(id));
  console.log(`\ncoverage: ${pool.length - unpicked.length}/${pool.length} collections picked at least once (${(((pool.length - unpicked.length) / pool.length) * 100).toFixed(1)}%)`);
  if (unpicked.length) {
    const index = buildIndex();
    const shown = SHOW_ALL_UNPICKED ? unpicked : unpicked.slice(0, 10);
    console.log(`  never picked (${unpicked.length}):`);
    for (const id of shown) {
      let label = id;
      try {
        label = path.relative(COLLECTIONS_ROOT, getCollection(index, id).dir);
      } catch {
        /* collection removed since it was indexed */
      }
      console.log(`    ${label}`);
    }
    if (!SHOW_ALL_UNPICKED && unpicked.length > shown.length) {
      console.log(`    ... and ${unpicked.length - shown.length} more (--unpicked for the full list)`);
    }
  }
}

// --- yield by collection: the input any future weighting would need ------
const stats = new Map();
for (const o of outcomes) {
  if (!o.path) continue;
  const s = stats.get(o.path) || { runs: 0, yielded: 0 };
  s.runs++;
  if (o.result !== 'none') s.yielded++;
  stats.set(o.path, s);
}
const multi = [...stats].filter(([, s]) => s.runs > 1);
if (multi.length) {
  console.log('\nper-collection yield (collections audited more than once):');
  for (const [p, s] of multi.sort((a, b) => b[1].runs - a[1].runs).slice(0, 15)) {
    console.log(`  ${s.yielded}/${s.runs}  ${p}`);
  }
}
