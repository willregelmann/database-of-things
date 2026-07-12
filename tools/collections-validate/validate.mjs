import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';
import Ajv from 'ajv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const COLLECTIONS_ROOT = path.join(REPO_ROOT, 'collections');
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const ajv = new Ajv({ allErrors: true, strict: false });
const seenIds = new Map();
const errors = [];

function rel(p) {
  return path.relative(REPO_ROOT, p);
}

function validateEntityStructure(filePath, data) {
  if (!data || typeof data !== 'object') {
    errors.push(`${rel(filePath)}: file does not contain a YAML object`);
    return;
  }
  for (const field of ['id', 'name', 'type']) {
    if (!data[field] || typeof data[field] !== 'string' || !data[field].trim()) {
      errors.push(`${rel(filePath)}: missing or empty required field "${field}"`);
    }
  }
  for (const field of ['collection', 'parent_collection']) {
    if (data[field] !== undefined) {
      errors.push(
        `${rel(filePath)}: has a "${field}" field — parent membership is derived from directory position, remove it`
      );
    }
  }
  if (data.id) {
    if (!UUID_RE.test(data.id)) {
      errors.push(`${rel(filePath)}: "id" is not a valid UUID: ${data.id}`);
    } else {
      const key = data.id.toLowerCase();
      const existing = seenIds.get(key);
      if (existing) {
        errors.push(`${rel(filePath)}: duplicate id ${data.id} (also used by ${rel(existing)})`);
      } else {
        seenIds.set(key, filePath);
      }
    }
  }
}

function walk(dir, inherited) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = entries.filter((e) => e.isFile()).map((e) => e.name);
  const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name);

  let { claudeMdPath, schema } = inherited;

  if (files.includes('CLAUDE.md')) {
    claudeMdPath = path.join(dir, 'CLAUDE.md');
  }
  if (files.includes('template.schema.json')) {
    const schemaPath = path.join(dir, 'template.schema.json');
    const schemaJson = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
    schema = ajv.compile(schemaJson);
  }

  const entityFiles = files.filter((f) => f.endsWith('.yaml') || f.endsWith('.yml'));

  if (entityFiles.length > 0 && !claudeMdPath) {
    errors.push(`${rel(dir)}: contains entity files but has no CLAUDE.md (own or inherited)`);
  }
  if (entityFiles.length > 0 && !schema) {
    errors.push(`${rel(dir)}: contains entity files but has no template.schema.json (own or inherited)`);
  }
  if (dir !== COLLECTIONS_ROOT && !files.includes('_collection.yaml')) {
    errors.push(`${rel(dir)}: missing _collection.yaml`);
  }

  for (const f of entityFiles) {
    const filePath = path.join(dir, f);
    const data = yaml.load(fs.readFileSync(filePath, 'utf8'));
    validateEntityStructure(filePath, data);

    if (f === '_collection.yaml') {
      if (data && data.type !== 'collection') {
        errors.push(`${rel(filePath)}: _collection.yaml must have type: collection`);
      }
    } else if (schema && data && data.attributes !== undefined) {
      const valid = schema(data.attributes);
      if (!valid) {
        for (const err of schema.errors) {
          errors.push(`${rel(filePath)}: attributes${err.instancePath} ${err.message}`);
        }
      }
    }
  }

  for (const d of dirs) {
    walk(path.join(dir, d), { claudeMdPath, schema });
  }
}

if (!fs.existsSync(COLLECTIONS_ROOT)) {
  console.error(`No collections/ directory found at ${COLLECTIONS_ROOT}`);
  process.exit(1);
}

walk(COLLECTIONS_ROOT, { claudeMdPath: null, schema: null });

if (errors.length > 0) {
  console.error(`✗ ${errors.length} validation error(s):\n`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
} else {
  console.log(`✓ collections/ valid (${seenIds.size} entities checked)`);
}
