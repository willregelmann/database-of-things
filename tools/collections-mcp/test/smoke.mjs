import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER_PATH = path.join(__dirname, '..', 'server.mjs');
const SCRATCH_CHANGELOG = path.join(__dirname, '.smoke-test-changelog.json');
const REPO_ROOT = path.join(__dirname, '..', '..', '..');
const SCRATCH_DIR = path.join(REPO_ROOT, 'collections', 'zzz-smoke-test-scratch');

function ok(label, cond) {
  console.log(`${cond ? 'ok' : 'FAIL'} - ${label}`);
  if (!cond) process.exitCode = 1;
}

// A throwaway collection with one item, just for exercising rename_item —
// created on disk before the server starts (so its index picks it up),
// removed at the end regardless of outcome.
fs.rmSync(SCRATCH_DIR, { recursive: true, force: true });
fs.mkdirSync(SCRATCH_DIR);
fs.copyFileSync(path.join(REPO_ROOT, 'collections', 'plush', 'CLAUDE.md'), path.join(SCRATCH_DIR, 'CLAUDE.md'));
fs.copyFileSync(path.join(REPO_ROOT, 'collections', 'plush', 'template.schema.json'), path.join(SCRATCH_DIR, 'template.schema.json'));
const SCRATCH_ITEM_ID = 'aaaaaaaa-1111-1111-1111-111111111111';
const SCRATCH_COLLECTION_ID = 'bbbbbbbb-1111-1111-1111-111111111111';
const SCRATCH_COMPONENT_ID = 'cccccccc-1111-1111-1111-111111111111';
fs.writeFileSync(
  path.join(SCRATCH_DIR, '_collection.yaml'),
  `id: ${SCRATCH_COLLECTION_ID}\nname: Smoke Test Scratch Collection\ntype: collection\n`
);
fs.writeFileSync(path.join(SCRATCH_DIR, 'wrong-name.yaml'), `id: ${SCRATCH_ITEM_ID}\nname: Test Item\ntype: plush\nattributes: {}\n`);
// A components bucket (leading underscore, no _collection.yaml of its own —
// see collections/CLAUDE.md, "Components") with one pre-existing component,
// for exercising list_components/upsert_component below.
const SCRATCH_BUCKET_DIR = path.join(SCRATCH_DIR, '_parts');
fs.mkdirSync(SCRATCH_BUCKET_DIR);
fs.writeFileSync(
  path.join(SCRATCH_BUCKET_DIR, 'existing-part.yaml'),
  `id: ${SCRATCH_COMPONENT_ID}\nname: Existing Part\ntype: plush\nattributes: {}\n`
);

const transport = new StdioClientTransport({
  command: 'node',
  args: [SERVER_PATH],
  env: { ...process.env, COLLECTIONS_MCP_CHANGELOG: SCRATCH_CHANGELOG },
});
const client = new Client({ name: 'collections-mcp-smoke', version: '0.0.0' });
await client.connect(transport);

const { tools } = await client.listTools();
const names = tools.map((t) => t.name).sort();
console.log('tools:', names.join(', '));
ok(
  'all 12 tools registered',
  [
    'choose_random_collection',
    'get_collection_context',
    'get_collection_details',
    'get_item_details',
    'list_collections',
    'list_items',
    'list_components',
    'upsert_collection',
    'upsert_item',
    'upsert_component',
    'rename_item',
    'flag_finding',
  ].every((n) => names.includes(n))
);

const chosen = await client.callTool({ name: 'choose_random_collection', arguments: {} });
ok('choose_random_collection did not error', !chosen.isError);
const { collection_id } = JSON.parse(chosen.content[0].text);
ok('choose_random_collection returned an id', typeof collection_id === 'string' && collection_id.length > 0);
console.log('chosen collection_id:', collection_id);

const details = await client.callTool({ name: 'get_collection_details', arguments: { collection_id } });
ok('get_collection_details did not error', !details.isError);
console.log('details:', details.content[0].text);

const context = await client.callTool({ name: 'get_collection_context', arguments: { collection_id } });
ok('get_collection_context did not error', !context.isError);
ok('get_collection_context includes root CLAUDE.md header', context.content[0].text.includes('collections/CLAUDE.md'));

const items = await client.callTool({ name: 'list_items', arguments: { collection_id } });
ok('list_items did not error', !items.isError);
const nested = await client.callTool({ name: 'list_collections', arguments: { collection_id } });
ok('list_collections did not error', !nested.isError);
console.log(`collection ${collection_id}: ${JSON.parse(items.content[0].text).length} items, ${JSON.parse(nested.content[0].text).length} nested collections`);

const badItem = await client.callTool({ name: 'get_item_details', arguments: { item_id: 'nonexistent' } });
ok('get_item_details on a bad id returns isError instead of throwing', badItem.isError === true);

const scratchDetails = await client.callTool({ name: 'get_collection_details', arguments: { collection_id: SCRATCH_COLLECTION_ID } });
ok('get_collection_details did not error (scratch)', !scratchDetails.isError);
const scratchDetailsBody = JSON.parse(scratchDetails.content[0].text);
ok(
  'get_collection_details reports the scratch components bucket',
  Array.isArray(scratchDetailsBody.componentBuckets) && scratchDetailsBody.componentBuckets.includes('parts')
);

const components = await client.callTool({ name: 'list_components', arguments: { collection_id: SCRATCH_COLLECTION_ID, bucket: 'parts' } });
ok('list_components did not error', !components.isError);
const componentsBody = JSON.parse(components.content[0].text);
ok('list_components finds the existing component', componentsBody.some((c) => c.id === SCRATCH_COMPONENT_ID));

const badBucket = await client.callTool({ name: 'list_components', arguments: { collection_id: SCRATCH_COLLECTION_ID, bucket: 'nonexistent' } });
ok('list_components on an unknown bucket returns isError', badBucket.isError === true);

const createdComponent = await client.callTool({
  name: 'upsert_component',
  arguments: {
    collection_id: SCRATCH_COLLECTION_ID,
    bucket: 'parts',
    component: { name: 'New Part', type: 'plush', filename: 'new-part.yaml', attributes: {} },
  },
});
ok('upsert_component (create) did not error', !createdComponent.isError);
ok('upsert_component actually wrote the file', fs.existsSync(path.join(SCRATCH_BUCKET_DIR, 'new-part.yaml')));

const badComponentBucket = await client.callTool({
  name: 'upsert_component',
  arguments: {
    collection_id: SCRATCH_COLLECTION_ID,
    bucket: 'nonexistent',
    component: { name: 'Bad Part', type: 'plush', filename: 'bad-part.yaml', attributes: {} },
  },
});
ok('upsert_component into an unknown bucket returns isError', badComponentBucket.isError === true);

const itemWithComponents = await client.callTool({
  name: 'upsert_item',
  arguments: { collection_id: SCRATCH_COLLECTION_ID, item: { id: SCRATCH_ITEM_ID, components: [SCRATCH_COMPONENT_ID] } },
});
ok('upsert_item accepts a components field referencing a real component', !itemWithComponents.isError);

const flagged = await client.callTool({
  name: 'flag_finding',
  arguments: { collection_id, title: 'smoke test finding', body: 'not a real finding, just exercising the tool' },
});
ok('flag_finding did not error', !flagged.isError);
const changelog = JSON.parse(fs.readFileSync(SCRATCH_CHANGELOG, 'utf8'));
ok('flag_finding appended a flag entry to the changelog', changelog.some((e) => e.kind === 'flag' && e.title === 'smoke test finding'));

const renamed = await client.callTool({
  name: 'rename_item',
  arguments: { item_id: SCRATCH_ITEM_ID, new_filename: 'correct-name.yaml' },
});
ok('rename_item did not error', !renamed.isError);
ok('rename_item actually moved the file', !fs.existsSync(path.join(SCRATCH_DIR, 'wrong-name.yaml')) && fs.existsSync(path.join(SCRATCH_DIR, 'correct-name.yaml')));
const badRename = await client.callTool({
  name: 'rename_item',
  arguments: { item_id: SCRATCH_ITEM_ID, new_filename: 'BadName.yaml' },
});
ok('rename_item rejects a non-conforming filename', badRename.isError === true);

await client.close();
fs.rmSync(SCRATCH_CHANGELOG, { force: true });
fs.rmSync(SCRATCH_DIR, { recursive: true, force: true });
console.log(process.exitCode ? '\nSMOKE TEST FAILED' : '\nSMOKE TEST PASSED');
