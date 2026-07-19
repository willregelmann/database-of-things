#!/usr/bin/env node
// Thin CLI transport over the same lib/*.mjs the MCP server uses — a
// fallback for environments (like a remote dispatch session) that can't
// (re)connect a newly-registered project MCP server mid-session. Same
// operations, same validation/rollback, just invoked via Bash instead of
// the MCP protocol.
import { buildIndex, getCollection, getItem, rel } from './lib/repo.mjs';
import { upsertItem, upsertComponent, upsertCollection, renameItem } from './lib/mutate.mjs';
import { appendEntry } from './lib/changelog.mjs';
import fs from 'node:fs';

const [, , cmd, ...rest] = process.argv;

function out(value) {
  console.log(typeof value === 'string' ? value : JSON.stringify(value, null, 2));
}

function fail(err) {
  console.error(err.message || String(err));
  process.exit(1);
}

const index = buildIndex();

try {
  switch (cmd) {
    case 'choose-random-collection': {
      if (index.collectionIds.length === 0) throw new Error('no collections found');
      const collection_id = index.collectionIds[Math.floor(Math.random() * index.collectionIds.length)];
      out({ collection_id });
      break;
    }
    case 'get-collection-context': {
      const node = getCollection(index, rest[0]);
      const parts = node.claudeChain.map((p) => `### ${rel(p)} ###\n\n${fs.readFileSync(p, 'utf8')}`);
      if (node.schemaPath) {
        parts.push(`### ${rel(node.schemaPath)} (attributes schema) ###\n\n${fs.readFileSync(node.schemaPath, 'utf8')}`);
      }
      out(parts.join('\n\n---\n\n'));
      break;
    }
    case 'get-collection-details': {
      const node = getCollection(index, rest[0]);
      out({ path: rel(node.path), ...node.data, componentBuckets: Object.keys(node.componentBuckets) });
      break;
    }
    case 'list-items': {
      out(getCollection(index, rest[0]).childItems);
      break;
    }
    case 'list-components': {
      const [collectionId, bucket] = rest;
      const node = getCollection(index, collectionId);
      const bucketNode = node.componentBuckets[bucket];
      if (!bucketNode) throw new Error(`collection ${collectionId} has no "_${bucket}" components bucket`);
      out(bucketNode.items);
      break;
    }
    case 'list-collections': {
      out(getCollection(index, rest[0]).childCollections);
      break;
    }
    case 'get-item-details': {
      const node = getItem(index, rest[0]);
      out({ path: rel(node.path), ...node.data });
      break;
    }
    case 'upsert-item': {
      const [collectionId, json] = rest;
      const result = upsertItem(index, { collectionId, item: JSON.parse(json) });
      appendEntry({ kind: 'item', collectionId, ...result });
      out(result);
      break;
    }
    case 'upsert-collection': {
      const [collectionId, json] = rest;
      const result = upsertCollection(index, { collectionId, collection: JSON.parse(json) });
      appendEntry({ kind: 'collection', collectionId, ...result });
      out(result);
      break;
    }
    case 'upsert-component': {
      const [collectionId, bucket, json] = rest;
      const result = upsertComponent(index, { collectionId, bucket, item: JSON.parse(json) });
      appendEntry({ kind: 'component', collectionId, bucket, ...result });
      out(result);
      break;
    }
    case 'flag-finding': {
      const [collectionId, title, body] = rest;
      const node = getCollection(index, collectionId);
      appendEntry({ kind: 'flag', collectionId, collectionPath: rel(node.path), title, body });
      out({ flagged: true });
      break;
    }
    case 'rename-item': {
      const [itemId, newFilename] = rest;
      const collectionId = getItem(index, itemId).collectionId;
      const result = renameItem(index, { itemId, newFilename });
      appendEntry({ kind: 'rename', entityKind: 'item', id: itemId, collectionId, ...result });
      out(result);
      break;
    }
    default:
      throw new Error(
        `unknown command "${cmd}" — expected one of: choose-random-collection, get-collection-context <id>, get-collection-details <id>, list-items <id>, list-components <collection_id> <bucket>, list-collections <id>, get-item-details <id>, upsert-item <collection_id> <json>, upsert-component <collection_id> <bucket> <json>, upsert-collection <collection_id> <json>, flag-finding <collection_id> <title> <body>, rename-item <item_id> <new_filename>`
      );
  }
} catch (err) {
  fail(err);
}
