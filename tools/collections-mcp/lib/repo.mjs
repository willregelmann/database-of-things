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
 * element.
 */
export function buildIndex() {
  const byId = new Map();
  const collectionIds = [];

  function walk(dir, claudeChain, schemaPath) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    const files = entries.filter((e) => e.isFile()).map((e) => e.name);
    const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name);

    let chain = claudeChain;
    if (files.includes('CLAUDE.md')) {
      chain = [...claudeChain, path.join(dir, 'CLAUDE.md')];
    }
    let schema = schemaPath;
    if (files.includes('template.schema.json')) {
      schema = path.join(dir, 'template.schema.json');
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
        schemaPath: schema,
        childItems: [],
        childCollections: [],
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
        collectionId: selfNode ? selfNode.id : null,
        claudeChain: chain,
        schemaPath: schema,
      };
      byId.set(data.id, node);
      if (selfNode) {
        selfNode.childItems.push({ id: data.id, name: data.name, type: data.type });
      }
    }

    for (const d of dirs.sort()) {
      const childId = walk(path.join(dir, d), chain, schema);
      if (selfNode && childId) {
        const child = byId.get(childId);
        selfNode.childCollections.push({ id: childId, name: child.name, type: child.type });
      }
    }

    return selfNode ? selfNode.id : null;
  }

  walk(COLLECTIONS_ROOT, [], null);
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
