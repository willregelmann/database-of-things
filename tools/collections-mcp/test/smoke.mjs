import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER_PATH = path.join(__dirname, '..', 'server.mjs');
const SCRATCH_CHANGELOG = path.join(__dirname, '.smoke-test-changelog.json');

function ok(label, cond) {
  console.log(`${cond ? 'ok' : 'FAIL'} - ${label}`);
  if (!cond) process.exitCode = 1;
}

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
  'all 9 tools registered',
  [
    'choose_random_collection',
    'get_collection_context',
    'get_collection_details',
    'get_item_details',
    'list_collections',
    'list_items',
    'upsert_collection',
    'upsert_item',
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

const flagged = await client.callTool({
  name: 'flag_finding',
  arguments: { collection_id, title: 'smoke test finding', body: 'not a real finding, just exercising the tool' },
});
ok('flag_finding did not error', !flagged.isError);
const changelog = JSON.parse(fs.readFileSync(SCRATCH_CHANGELOG, 'utf8'));
ok('flag_finding appended a flag entry to the changelog', changelog.some((e) => e.kind === 'flag' && e.title === 'smoke test finding'));

await client.close();
fs.rmSync(SCRATCH_CHANGELOG, { force: true });
console.log(process.exitCode ? '\nSMOKE TEST FAILED' : '\nSMOKE TEST PASSED');
