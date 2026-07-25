import fs from 'node:fs';
import path from 'node:path';
import { REPO_ROOT } from './repo.mjs';

// Append-only record of what the audit loop actually did, one JSON object per
// line. Purely observational: nothing reads it to make a decision, and no
// scheduling behaviour depends on it. It exists because none of the basic
// questions about the loop were answerable — which collections have never been
// picked, how often one comes back around, whether the ~2/3 no-change rate is
// converging or just the sampler being uninformed. Any future argument about
// scheduling policy should be settled with this file rather than with
// reasoning about it.
//
// Deliberately NOT committed (see .gitignore), and local to whichever checkout
// runs the job. The alternative — flushing it into each audit PR — would put a
// constantly-rewritten file in every branch the review cron merges, and two
// open audit PRs would then conflict on it and jam the pipeline. A run that
// changes nothing has no PR to ride along with anyway, and those are exactly
// the runs currently invisible. Local and durable-enough beats committed and
// self-jamming. The dedicated audit checkout keeps it across ticks: the sync
// step is `git checkout --detach origin/main`, which leaves untracked files
// alone.
const LEDGER_PATH =
  process.env.COLLECTIONS_MCP_LEDGER || path.join(REPO_ROOT, 'tools', 'collections-mcp', 'audit-ledger.jsonl');

/**
 * Appends one entry. Never throws: instrumentation must not be able to take
 * down an audit run. A lost line is a gap in the data; a thrown error here
 * would be a lost run.
 */
export function append(entry) {
  try {
    fs.appendFileSync(LEDGER_PATH, `${JSON.stringify({ ts: new Date().toISOString(), ...entry })}\n`);
  } catch {
    // intentionally swallowed — see above
  }
}

/** Every entry, oldest first. Malformed lines are skipped, not fatal. */
export function readAll() {
  try {
    return fs
      .readFileSync(LEDGER_PATH, 'utf8')
      .split('\n')
      .filter((l) => l.trim())
      .map((l) => {
        try {
          return JSON.parse(l);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
  } catch {
    return [];
  }
}

/**
 * The most recent `pick`, so submit.mjs can attribute a run's outcome without
 * the two processes sharing state. One server process audits one collection
 * (the skill's "one level only" rule, which submit.mjs already relies on to
 * label its PR), so the last pick is this run's pick. If a session somehow
 * picks twice, the earlier pick simply ends up with no outcome recorded —
 * which is itself worth seeing.
 */
export function lastPick() {
  const entries = readAll();
  for (let i = entries.length - 1; i >= 0; i--) {
    if (entries[i].event === 'pick') return entries[i];
  }
  return null;
}

export function ledgerPath() {
  return LEDGER_PATH;
}
