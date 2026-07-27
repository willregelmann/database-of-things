#!/usr/bin/env node
/**
 * schema-scope — answers the three questions you need answered before touching
 * an item-attributes.schema.json in this repo:
 *
 *   which <path>     Which template(s) govern this file/directory, and what's
 *                    the effective merged schema?
 *   scope <path>     Which entity files does a given template actually govern?
 *   keys  <path>     What does the real data under it look like — every
 *                    `attributes` key, how many files carry it, and the value
 *                    distribution (so an enum/required/pattern is written
 *                    against the data instead of against a guess).
 *
 * Resolution mirrors tools/collections-validate/validate.mjs exactly: walk down
 * from collections/ and tags/, and a directory's own item-attributes.schema.json
 * *layers onto* the inherited one for that subtree (`properties` merge, `required` unions,
 * `additionalProperties` takes the nearest declared value) rather than
 * replacing it — see the json-schema skill's fact 2.
 */

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Repo root = nearest ancestor of cwd holding both collections/ and tags/. */
function findRepoRoot() {
  const candidates = [process.cwd(), path.resolve(__dirname, '..', '..', '..', '..')];
  for (const start of candidates) {
    let cur = start;
    for (;;) {
      if (fs.existsSync(path.join(cur, 'collections')) && fs.existsSync(path.join(cur, 'tags'))) {
        return cur;
      }
      const up = path.dirname(cur);
      if (up === cur) break;
      cur = up;
    }
  }
  console.error('Could not locate the repo root (no ancestor has both collections/ and tags/).');
  process.exit(1);
}

const REPO_ROOT = findRepoRoot();
const ROOTS = [path.join(REPO_ROOT, 'collections'), path.join(REPO_ROOT, 'tags')];

let yaml;
try {
  const require = createRequire(path.join(REPO_ROOT, 'tools', 'collections-validate', 'package.json'));
  yaml = require('js-yaml');
} catch {
  console.error('js-yaml not found. Run: cd tools/collections-validate && npm install');
  process.exit(1);
}

const rel = (p) => path.relative(REPO_ROOT, p);

/** Mirrors validate.mjs's mergeProperty/mergeAttributesSchema exactly — keep in sync. */
function mergeProperty(parentProp, childProp) {
  if (!parentProp) return childProp;
  if (!childProp) return parentProp;
  if (Array.isArray(parentProp.enum) && Array.isArray(childProp.enum)) {
    return { ...parentProp, ...childProp, enum: [...new Set([...parentProp.enum, ...childProp.enum])] };
  }
  if (
    parentProp.type === 'array' &&
    childProp.type === 'array' &&
    Array.isArray(parentProp.items && parentProp.items.enum) &&
    Array.isArray(childProp.items && childProp.items.enum)
  ) {
    return {
      ...parentProp,
      ...childProp,
      items: {
        ...parentProp.items,
        ...childProp.items,
        enum: [...new Set([...parentProp.items.enum, ...childProp.items.enum])],
      },
    };
  }
  return childProp;
}

function mergeAttributesSchema(parent, child) {
  if (!parent) return child;
  if (!child) return parent;
  const properties = { ...(parent.properties || {}) };
  for (const [key, childProp] of Object.entries(child.properties || {})) {
    properties[key] = mergeProperty(properties[key], childProp);
  }
  return {
    type: 'object',
    properties,
    required: [...new Set([...(parent.required || []), ...(child.required || [])])],
    additionalProperties: child.additionalProperties !== undefined ? child.additionalProperties : parent.additionalProperties,
  };
}

/**
 * Walks the tree once, recording for every directory the schema chain
 * (root to nearest, mirroring claudeChain/schemaChain in
 * tools/collections-mcp/lib/repo.mjs), the merged effective schema, and
 * CLAUDE.md in force there, plus the entity files it holds.
 */
function index() {
  const dirs = new Map(); // absolute dir -> { schemaChain, schemaJson, claudeMdPath, entityFiles }

  function walk(dir, inherited) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const files = entries.filter((e) => e.isFile()).map((e) => e.name);

    let { schemaChain, schemaJson, claudeMdPath } = inherited;
    if (files.includes('item-attributes.schema.json')) {
      const p = path.join(dir, 'item-attributes.schema.json');
      const own = JSON.parse(fs.readFileSync(p, 'utf8'));
      schemaChain = [...schemaChain, p];
      schemaJson = mergeAttributesSchema(schemaJson, own);
    }
    if (files.includes('CLAUDE.md')) claudeMdPath = path.join(dir, 'CLAUDE.md');

    const entityFiles = files.filter((f) => f.endsWith('.yaml') || f.endsWith('.yml'));
    dirs.set(dir, { schemaChain, schemaJson, claudeMdPath, entityFiles });

    for (const e of entries.filter((e) => e.isDirectory())) {
      walk(path.join(dir, e.name), { schemaChain, schemaJson, claudeMdPath });
    }
  }

  for (const root of ROOTS) walk(root, { schemaChain: [], schemaJson: null, claudeMdPath: null });
  return dirs;
}

/**
 * Resolves a user-supplied path: relative to cwd first, then to the repo root,
 * so both `collections/plush` from the root and `.` from inside it work.
 */
function resolvePath(argPath) {
  const arg = argPath || '.';
  for (const base of [process.cwd(), REPO_ROOT]) {
    const abs = path.resolve(base, arg);
    if (fs.existsSync(abs)) return abs;
  }
  console.error(`No such path: ${arg}`);
  process.exit(1);
}

/** Resolves a user-supplied path to the directory whose context applies. */
function targetDir(argPath) {
  const abs = resolvePath(argPath);
  return fs.statSync(abs).isDirectory() ? abs : path.dirname(abs);
}

function cmdWhich(argPath) {
  const dirs = index();
  const dir = targetDir(argPath);
  const ctx = dirs.get(dir);
  if (!ctx) {
    console.error(`${rel(dir)} is not under collections/ or tags/ — no template applies.`);
    process.exit(1);
  }
  console.log(`path:      ${rel(dir)}`);
  console.log(`CLAUDE.md: ${ctx.claudeMdPath ? rel(ctx.claudeMdPath) : '(none — validator will error)'}`);
  if (ctx.schemaChain.length === 0) {
    console.log('schema chain: (none — fine unless something under this path sets `attributes`, in which case the validator will error)');
    return;
  }
  console.log(`schema chain (root to nearest — each layers onto the ones before it):`);
  for (const p of ctx.schemaChain) console.log(`  ${rel(p)}`);
  console.log('\n--- effective merged schema (what actually governs attributes here) ---');
  console.log(JSON.stringify(ctx.schemaJson, null, 2));
}

/** Every entity file whose schema chain includes `schemaPath` — i.e. every
 * file this template's own properties/required actually reach, own or
 * inherited-and-merged into something more specific below it. */
function governedFiles(dirs, schemaPath) {
  const out = [];
  for (const [dir, ctx] of dirs) {
    if (!ctx.schemaChain.includes(schemaPath)) continue;
    for (const f of ctx.entityFiles) out.push(path.join(dir, f));
  }
  return out.sort();
}

function resolveSchemaPath(dirs, argPath) {
  const abs = resolvePath(argPath);
  if (!fs.statSync(abs).isDirectory() && abs.endsWith('item-attributes.schema.json')) {
    return abs;
  }
  const ctx = dirs.get(targetDir(argPath));
  if (!ctx || ctx.schemaChain.length === 0) {
    console.error(`No item-attributes.schema.json governs ${argPath}.`);
    process.exit(1);
  }
  return ctx.schemaChain[ctx.schemaChain.length - 1];
}

function cmdScope(argPath) {
  const dirs = index();
  const schemaPath = resolveSchemaPath(dirs, argPath);
  const files = governedFiles(dirs, schemaPath);
  const items = files.filter((f) => path.basename(f) !== '_collection.yaml');
  const collections = files.length - items.length;

  console.log(`template: ${rel(schemaPath)}`);
  console.log(`governs:  ${items.length} item file(s) — these are schema-checked`);
  console.log(`          ${collections} _collection.yaml — NOT schema-checked by the validator`);

  const byDir = new Map();
  for (const f of items) {
    const d = path.dirname(f);
    byDir.set(d, (byDir.get(d) || 0) + 1);
  }
  const sorted = [...byDir.entries()].sort((a, b) => b[1] - a[1]);
  console.log(`\ndirectories holding governed items (${sorted.length}):`);
  for (const [d, n] of sorted.slice(0, 30)) console.log(`  ${String(n).padStart(5)}  ${rel(d)}`);
  if (sorted.length > 30) console.log(`  ... and ${sorted.length - 30} more`);
  console.log('\nAny change to this template is retroactive: every file above is re-checked.');
}

function cmdKeys(argPath, { max = 25 } = {}) {
  const dirs = index();
  const schemaPath = resolveSchemaPath(dirs, argPath);
  const files = governedFiles(dirs, schemaPath).filter((f) => path.basename(f) !== '_collection.yaml');

  const total = files.length;
  const keys = new Map(); // key -> { count, values: Map, types: Set }
  let noAttributes = 0;

  for (const f of files) {
    let data;
    try {
      data = yaml.load(fs.readFileSync(f, 'utf8'));
    } catch (e) {
      console.error(`  ! unparseable: ${rel(f)} (${e.message})`);
      continue;
    }
    const attrs = data && data.attributes;
    if (attrs === undefined || attrs === null || typeof attrs !== 'object') {
      noAttributes++;
      continue;
    }
    for (const [k, v] of Object.entries(attrs)) {
      if (!keys.has(k)) keys.set(k, { count: 0, values: new Map(), types: new Set() });
      const rec = keys.get(k);
      rec.count++;
      rec.types.add(Array.isArray(v) ? 'array' : v === null ? 'null' : typeof v);
      const key = typeof v === 'object' ? JSON.stringify(v) : String(v);
      rec.values.set(key, (rec.values.get(key) || 0) + 1);
    }
  }

  console.log(`template: ${rel(schemaPath)}`);
  console.log(`items:    ${total} governed item file(s)`);
  if (noAttributes > 0) {
    console.log(`          ${noAttributes} have no \`attributes:\` — the validator skips those entirely`);
  }
  console.log('');

  const sorted = [...keys.entries()].sort((a, b) => b[1].count - a[1].count);
  for (const [k, rec] of sorted) {
    const pct = total ? ((100 * rec.count) / total).toFixed(1) : '0.0';
    const universal = rec.count === total && total > 0 ? '  <- present on every item (required candidate)' : '';
    console.log(`${k}  —  ${rec.count}/${total} (${pct}%)  types: ${[...rec.types].join('|')}${universal}`);
    const vals = [...rec.values.entries()].sort((a, b) => b[1] - a[1]);
    if (vals.length <= max) {
      console.log(`  ${vals.length} distinct value(s) — closed vocabulary, enum candidate:`);
      for (const [v, n] of vals) console.log(`    ${String(n).padStart(5)}  ${v}`);
    } else {
      console.log(`  ${vals.length} distinct values — too open for an enum; top ${max}:`);
      for (const [v, n] of vals.slice(0, max)) console.log(`    ${String(n).padStart(5)}  ${v}`);
    }
    console.log('');
  }
  if (sorted.length === 0) console.log('(no attributes found on any governed item)');
}

const [cmd, argPath, ...rest] = process.argv.slice(2);
const maxArg = rest.find((a) => a.startsWith('--max='));
const max = maxArg ? Number(maxArg.slice('--max='.length)) : 25;

switch (cmd) {
  case 'which':
    cmdWhich(argPath);
    break;
  case 'scope':
    cmdScope(argPath);
    break;
  case 'keys':
    cmdKeys(argPath, { max });
    break;
  default:
    console.log(`Usage:
  node schema-scope.mjs which <path>            which template + CLAUDE.md govern this path
  node schema-scope.mjs scope <path>            which entity files that template governs
  node schema-scope.mjs keys  <path> [--max=N]  attribute keys + value distribution of the real data

<path> may be a directory, an entity .yaml, or an item-attributes.schema.json.
Paths are relative to the repo root or to cwd.`);
    process.exit(cmd ? 1 : 0);
}
