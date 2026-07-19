import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import yaml from 'js-yaml';
import { REPO_ROOT, rel, getCollection, getItem } from './repo.mjs';

const FILENAME_RE = /^[a-z0-9]+(-[a-z0-9]+)*\.ya?ml$/;

const VALIDATE_DIR = path.join(REPO_ROOT, 'tools', 'collections-validate');

/** Runs the full collections/ validator. Returns { ok, output }. */
function runValidator() {
  try {
    const output = execFileSync('node', ['validate.mjs'], {
      cwd: VALIDATE_DIR,
      encoding: 'utf8',
    });
    return { ok: true, output };
  } catch (err) {
    return { ok: false, output: `${err.stdout || ''}${err.stderr || ''}` };
  }
}

// Fields that are transport-only (routing/path construction), never written
// into the entity file itself.
const NON_DATA_FIELDS = new Set(['id', 'filename', 'directory']);

/**
 * Merges every field the caller provided (other than id/filename/directory,
 * which are transport-only) onto the existing entity — this is a generic
 * passthrough rather than a fixed whitelist, so category-specific top-level
 * fields (e.g. Pokémon TCG/MTG's `total_cards`) work without the tool
 * needing to know about every category's own conventions. `attributes` is
 * merged key-by-key rather than replaced outright, since items commonly
 * patch a single attribute at a time.
 */
function applyPatch(existingData, patch) {
  const result = existingData ? { ...existingData } : {};
  for (const [key, value] of Object.entries(patch)) {
    if (NON_DATA_FIELDS.has(key) || value === undefined) continue;
    if (key === 'attributes') {
      result.attributes = existingData && existingData.attributes ? { ...existingData.attributes, ...value } : { ...value };
    } else {
      result[key] = value;
    }
  }
  return result;
}

/**
 * Create (no `item.id`) or update (`item.id` present) an item within
 * `collectionId`. Never moves/renames an existing item's file. Every
 * mutation is validated with the full validator after writing; on failure
 * the write is rolled back and an error is thrown with the validator output.
 */
export function upsertItem(index, { collectionId, item }) {
  const collection = getCollection(index, collectionId);
  let writePath;
  let originalRaw = null;
  let action;
  let before = null;
  let entityId;

  if (item.id) {
    const existing = getItem(index, item.id);
    if (existing.collectionId !== collectionId) {
      throw new Error(
        `item ${item.id} belongs to collection ${existing.collectionId}, not ${collectionId} — upsert_item never moves items between collections`
      );
    }
    writePath = existing.path;
    originalRaw = fs.readFileSync(writePath, 'utf8');
    before = existing.data;
    const merged = applyPatch(existing.data, item);
    fs.writeFileSync(writePath, yaml.dump(merged, { sortKeys: false }));
    action = 'update';
    entityId = item.id;
  } else {
    if (!item.filename) {
      throw new Error('creating a new item requires a "filename" (this repo\'s naming convention is category-specific — see get_collection_context)');
    }
    if (!item.name || !item.type) {
      throw new Error('creating a new item requires "name" and "type"');
    }
    writePath = path.join(collection.dir, item.filename);
    if (fs.existsSync(writePath)) {
      throw new Error(`${rel(writePath)} already exists`);
    }
    entityId = crypto.randomUUID();
    const merged = { id: entityId, ...applyPatch(null, item) };
    fs.writeFileSync(writePath, yaml.dump(merged, { sortKeys: false }));
    action = 'create';
  }

  const result = runValidator();
  if (!result.ok) {
    if (action === 'create') {
      fs.unlinkSync(writePath);
    } else {
      fs.writeFileSync(writePath, originalRaw);
    }
    throw new Error(`validation failed, change rolled back:\n${result.output}`);
  }

  const after = yaml.load(fs.readFileSync(writePath, 'utf8'));
  return { id: entityId, path: rel(writePath), action, before, after };
}

/**
 * Renames an existing item's file in place (same directory, new filename
 * only) — the one structural operation the tool surface exposes, added
 * because a real audit run found a genuine naming-convention violation
 * (stray suffixes on a reprint pair) it had no way to fix. Still narrow:
 * no moving between collections, no directory renames, and the full
 * validator gates it exactly like every other write.
 */
export function renameItem(index, { itemId, newFilename }) {
  const node = getItem(index, itemId);
  if (!FILENAME_RE.test(newFilename)) {
    throw new Error(`"${newFilename}" must be a lowercase, hyphenated filename ending in .yaml (e.g. "004-charizard.yaml")`);
  }
  const oldPath = node.path;
  const newPath = path.join(node.dir, newFilename);
  if (newPath === oldPath) {
    throw new Error(`item ${itemId} is already named ${newFilename}`);
  }
  if (fs.existsSync(newPath)) {
    throw new Error(`${rel(newPath)} already exists`);
  }

  fs.renameSync(oldPath, newPath);

  const result = runValidator();
  if (!result.ok) {
    fs.renameSync(newPath, oldPath);
    throw new Error(`validation failed, rename rolled back:\n${result.output}`);
  }

  return { id: itemId, oldPath: rel(oldPath), newPath: rel(newPath) };
}

/**
 * Create (no `collection.id`) or update (`collection.id` present) a
 * collection record. Creating nests a new directory + `_collection.yaml`
 * under `collectionId` (the parent) and inherits its CLAUDE.md/schema —
 * it never authors a new CLAUDE.md/template.schema.json, so bootstrapping
 * a genuinely new category is out of scope for this tool.
 */
export function upsertCollection(index, { collectionId, collection }) {
  let writePath;
  let originalRaw = null;
  let action;
  let before = null;
  let entityId;
  let newDir = null;

  if (collection.id) {
    const existing = getCollection(index, collection.id);
    writePath = existing.path;
    originalRaw = fs.readFileSync(writePath, 'utf8');
    before = existing.data;
    const merged = applyPatch(existing.data, collection);
    merged.type = 'collection'; // always "collection", regardless of what the caller passed
    fs.writeFileSync(writePath, yaml.dump(merged, { sortKeys: false }));
    action = 'update';
    entityId = collection.id;
  } else {
    const parent = getCollection(index, collectionId);
    if (!collection.directory) {
      throw new Error('creating a new collection requires a "directory" slug to nest it under the parent');
    }
    if (!collection.name) {
      throw new Error('creating a new collection requires a "name"');
    }
    newDir = path.join(parent.dir, collection.directory);
    if (fs.existsSync(newDir)) {
      throw new Error(`${rel(newDir)} already exists`);
    }
    entityId = crypto.randomUUID();
    const patched = applyPatch(null, collection);
    delete patched.type; // always "collection", regardless of what the caller passed
    const merged = { id: entityId, type: 'collection', ...patched };
    fs.mkdirSync(newDir);
    writePath = path.join(newDir, '_collection.yaml');
    fs.writeFileSync(writePath, yaml.dump(merged, { sortKeys: false }));
    action = 'create';
  }

  const result = runValidator();
  if (!result.ok) {
    if (action === 'create') {
      fs.rmSync(newDir, { recursive: true, force: true });
    } else {
      fs.writeFileSync(writePath, originalRaw);
    }
    throw new Error(`validation failed, change rolled back:\n${result.output}`);
  }

  const after = yaml.load(fs.readFileSync(writePath, 'utf8'));
  return { id: entityId, path: rel(writePath), action, before, after };
}
