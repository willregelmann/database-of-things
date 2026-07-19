import fs from 'node:fs';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { buildIndex, getCollection, getItem, rel } from './lib/repo.mjs';
import { upsertItem, upsertCollection } from './lib/mutate.mjs';
import { appendEntry } from './lib/changelog.mjs';

// Rebuilt after every successful write so reads in the same session see it.
let index = buildIndex();

function text(value) {
  return { content: [{ type: 'text', text: typeof value === 'string' ? value : JSON.stringify(value, null, 2) }] };
}

function errorText(err) {
  return { content: [{ type: 'text', text: err.message || String(err) }], isError: true };
}

const server = new McpServer({ name: 'collections-mcp', version: '0.1.0' });

server.registerTool(
  'choose_random_collection',
  {
    title: 'Choose a random collection',
    description:
      'Pick one collection directory uniformly at random from all of collections/** (any level — domain family, category, series, set, etc.). Returns its id for use with the other tools.',
    inputSchema: {},
  },
  async () => {
    try {
      if (index.collectionIds.length === 0) throw new Error('no collections found under collections/');
      const collection_id = index.collectionIds[Math.floor(Math.random() * index.collectionIds.length)];
      return text({ collection_id });
    } catch (err) {
      return errorText(err);
    }
  }
);

server.registerTool(
  'get_collection_context',
  {
    title: 'Get a collection\'s applicable curation guidance',
    description:
      'Returns every CLAUDE.md that applies to this collection, concatenated from the root collections/CLAUDE.md down through domain family, category, any intermediate overrides, to the collection\'s own (if it has one), plus its resolved template.schema.json. Read this before auditing or upserting anything in the collection.',
    inputSchema: { collection_id: z.string().describe('The collection id, e.g. from choose_random_collection') },
  },
  async ({ collection_id }) => {
    try {
      const node = getCollection(index, collection_id);
      const parts = node.claudeChain.map(
        (p) => `### ${rel(p)} ###\n\n${fs.readFileSync(p, 'utf8')}`
      );
      if (node.schemaPath) {
        parts.push(`### ${rel(node.schemaPath)} (attributes schema) ###\n\n${fs.readFileSync(node.schemaPath, 'utf8')}`);
      }
      return text(parts.join('\n\n---\n\n'));
    } catch (err) {
      return errorText(err);
    }
  }
);

server.registerTool(
  'get_collection_details',
  {
    title: 'Get a collection\'s own record',
    description: 'Returns the parsed _collection.yaml for this collection id.',
    inputSchema: { collection_id: z.string() },
  },
  async ({ collection_id }) => {
    try {
      const node = getCollection(index, collection_id);
      return text({ path: rel(node.path), ...node.data });
    } catch (err) {
      return errorText(err);
    }
  }
);

server.registerTool(
  'list_items',
  {
    title: 'List a collection\'s direct items',
    description: 'Lists the leaf item entities (not nested collections) directly inside this collection, as {id, name, type}.',
    inputSchema: { collection_id: z.string() },
  },
  async ({ collection_id }) => {
    try {
      const node = getCollection(index, collection_id);
      return text(node.childItems);
    } catch (err) {
      return errorText(err);
    }
  }
);

server.registerTool(
  'list_collections',
  {
    title: 'List a collection\'s direct nested collections',
    description: 'Lists the nested collection entities (not items) directly inside this collection, as {id, name, type}.',
    inputSchema: { collection_id: z.string() },
  },
  async ({ collection_id }) => {
    try {
      const node = getCollection(index, collection_id);
      return text(node.childCollections);
    } catch (err) {
      return errorText(err);
    }
  }
);

server.registerTool(
  'get_item_details',
  {
    title: 'Get an item\'s full record',
    description: 'Returns the parsed entity file for this item id.',
    inputSchema: { item_id: z.string() },
  },
  async ({ item_id }) => {
    try {
      const node = getItem(index, item_id);
      return text({ path: rel(node.path), ...node.data });
    } catch (err) {
      return errorText(err);
    }
  }
);

const itemFieldsShape = {
  id: z.string().optional().describe('Omit to create a new item; provide an existing item id to update it in place.'),
  name: z.string().optional(),
  type: z.string().optional(),
  date: z.string().optional(),
  attributes: z.record(z.any()).optional().describe('Merged key-by-key into any existing attributes on update.'),
  image: z.object({ source_url: z.string() }).optional(),
  tags: z.array(z.string()).optional(),
  filename: z
    .string()
    .optional()
    .describe('Required when creating a new item — the filename to write, following the category\'s naming convention.'),
};

server.registerTool(
  'upsert_item',
  {
    title: 'Create or update an item',
    description:
      'Creates a new item (omit "id") or patches fields on an existing one (provide "id") within the given collection. Never renames/moves a file. Validates against the full collections/ validator after writing and rolls back the write if it fails.',
    inputSchema: {
      collection_id: z.string(),
      item: z.object(itemFieldsShape),
    },
  },
  async ({ collection_id, item }) => {
    try {
      const result = upsertItem(index, { collectionId: collection_id, item });
      appendEntry({ kind: 'item', collectionId: collection_id, ...result });
      index = buildIndex();
      return text(result);
    } catch (err) {
      return errorText(err);
    }
  }
);

const collectionFieldsShape = {
  id: z.string().optional().describe('Omit to create a new nested collection; provide an existing collection id to update it in place.'),
  name: z.string().optional(),
  date: z.string().optional(),
  description: z.string().optional(),
  category: z.string().optional(),
  image: z.object({ source_url: z.string() }).optional(),
  tags: z.array(z.string()).optional(),
  directory: z
    .string()
    .optional()
    .describe('Required when creating — the new subdirectory name to nest under collection_id.'),
};

server.registerTool(
  'upsert_collection',
  {
    title: 'Create or update a collection',
    description:
      'Creates a new nested collection under collection_id (omit "id"; inherits the parent\'s CLAUDE.md/schema — does not author new curation conventions) or patches fields on an existing collection\'s own record (provide "id"). Validates and rolls back on failure, same as upsert_item.',
    inputSchema: {
      collection_id: z.string().describe('For create: the parent to nest under. For update: any valid id (ignored — "id" inside collection selects the target).'),
      collection: z.object(collectionFieldsShape),
    },
  },
  async ({ collection_id, collection }) => {
    try {
      const result = upsertCollection(index, { collectionId: collection_id, collection });
      appendEntry({ kind: 'collection', collectionId: collection_id, ...result });
      index = buildIndex();
      return text(result);
    } catch (err) {
      return errorText(err);
    }
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
