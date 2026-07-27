import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
export const COLLECTIONS_ROOT = path.join(REPO_ROOT, 'collections');

export function rel(p) {
  return path.relative(REPO_ROOT, p);
}

/**
 * Walks collections/ once and returns an index of every entity (collection
 * and item) keyed by id, plus a flat list of collection ids to sample from.
 * Each collection node's `claudeChain` is every CLAUDE.md from collections/
 * down to that directory (inclusive), not just the nearest one — callers
 * that want "the nearest applicable CLAUDE.md" can just take the last
 * element. `schemaChain` works the same way, and for the same reason: a
 * directory's own schema.json layers attributes on top of what it
 * inherited rather than replacing it (see validate.mjs's
 * mergeAttributesSchema), so a caller that only read the nearest schema.json
 * would miss attributes recommended at a family/category level.
 */
export function buildIndex() {
  const byId = new Map();
  const collectionIds = [];

  // `componentOwner` is set only while walking a components-bucket directory
  // (name prefixed with `_`, other than `_collection.yaml` itself — see
  // collections/CLAUDE.md, "Components"). Such a directory never has its own
  // `_collection.yaml`/id; its items belong to the nearest ancestor
  // collection's named bucket instead of that ancestor's own `childItems`.
  function walk(dir, claudeChain, schemaChain, componentOwner) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const files = entries.filter((e) => e.isFile()).map((e) => e.name);
    const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name);

    let chain = claudeChain;
    if (files.includes('CLAUDE.md')) {
      chain = [...claudeChain, path.join(dir, 'CLAUDE.md')];
    }
    let schema = schemaChain;
    if (files.includes('schema.json')) {
      schema = [...schemaChain, path.join(dir, 'schema.json')];
    }

    let selfNode = null;
    if (files.includes('_collection.yaml')) {
      const p = path.join(dir, '_collection.yaml');
      const data = yaml.load(fs.readFileSync(p, 'utf8'));
      if (!data || !data.id) {
        throw new Error(`${rel(p)}: missing or invalid id — run the validator before using this tool`);
      }
      selfNode = {
        kind: 'collection',
        id: data.id,
        name: data.name,
        type: data.type,
        dir,
        path: p,
        data,
        claudeChain: chain,
        schemaChain: schema,
        childItems: [],
        childCollections: [],
        componentBuckets: {},
      };
      byId.set(data.id, selfNode);
      collectionIds.push(data.id);
    }

    const itemFiles = files
      .filter((f) => (f.endsWith('.yaml') || f.endsWith('.yml')) && f !== '_collection.yaml')
      .sort();
    for (const f of itemFiles) {
      const p = path.join(dir, f);
      const data = yaml.load(fs.readFileSync(p, 'utf8'));
      if (!data || !data.id) {
        throw new Error(`${rel(p)}: missing or invalid id — run the validator before using this tool`);
      }
      const node = {
        kind: 'item',
        id: data.id,
        name: data.name,
        type: data.type,
        dir,
        path: p,
        data,
        collectionId: componentOwner ? componentOwner.collectionId : selfNode ? selfNode.id : null,
        bucket: componentOwner ? componentOwner.bucket : null,
        claudeChain: chain,
        schemaChain: schema,
      };
      byId.set(data.id, node);
      if (componentOwner) {
        componentOwner.bucketItems.push({ id: data.id, name: data.name, type: data.type });
      } else if (selfNode) {
        selfNode.childItems.push({ id: data.id, name: data.name, type: data.type });
      }
    }

    for (const d of dirs.sort()) {
      if (d.startsWith('_')) {
        if (selfNode) {
          const bucketName = d.slice(1);
          const bucket = { dir: path.join(dir, d), items: [] };
          selfNode.componentBuckets[bucketName] = bucket;
          walk(bucket.dir, chain, schema, { collectionId: selfNode.id, bucket: bucketName, bucketItems: bucket.items });
        }
        continue;
      }
      const childId = walk(path.join(dir, d), chain, schema, null);
      if (selfNode && childId) {
        const child = byId.get(childId);
        selfNode.childCollections.push({ id: childId, name: child.name, type: child.type });
      }
    }

    return selfNode ? selfNode.id : null;
  }

  walk(COLLECTIONS_ROOT, [], [], null);
  return { byId, collectionIds };
}

export function getCollection(index, id) {
  const node = index.byId.get(id);
  if (!node || node.kind !== 'collection') {
    throw new Error(`no collection with id ${id}`);
  }
  return node;
}

export function getItem(index, id) {
  const node = index.byId.get(id);
  if (!node || node.kind !== 'item') {
    throw new Error(`no item with id ${id}`);
  }
  return node;
}

export const LIST_ITEMS_DEFAULT_LIMIT = 200;
export const LIST_ITEMS_MAX_LIMIT = 1000;

/**
 * Shapes a collection's `childItems` into one page.
 *
 * Two savings, and they are not the same size. Hoisting `type` out of every
 * row is exact rather than lossy — it is uniform across all 287 collections
 * that currently hold items, so reporting it once loses nothing — but it only
 * trims about 18% of the payload. The bulk is the 36-character UUID on every
 * row, which is why the page window is what actually makes a large collection
 * readable: Squishmallows' 2,321 items serialize to ~66k tokens whole, more
 * than an audit session can spend on merely *listing* a collection before it
 * has verified anything (see issue #178).
 *
 * `total` is always the full count, so a caller can tell a page from the whole
 * collection without a second call — and a sampling caller knows what it is
 * sampling from.
 */
export function pageItems(childItems, { offset = 0, limit = LIST_ITEMS_DEFAULT_LIMIT } = {}) {
  const total = childItems.length;
  const start = Math.max(0, Math.min(offset, total));
  const size = Math.max(1, Math.min(limit, LIST_ITEMS_MAX_LIMIT));
  const page = childItems.slice(start, start + size);
  const types = new Set(childItems.map((i) => i.type));
  return {
    total,
    offset: start,
    returned: page.length,
    has_more: start + page.length < total,
    // Uniform in every collection today; if that ever stops being true the
    // per-item `type` comes back rather than this reporting a half-truth.
    item_type: types.size === 1 ? [...types][0] : null,
    items: types.size === 1 ? page.map(({ id, name }) => ({ id, name })) : page,
  };
}
