import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';
import Ajv from 'ajv';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const COLLECTIONS_ROOT = path.join(REPO_ROOT, 'collections');
const TAGS_ROOT = path.join(REPO_ROOT, 'tags');
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_RE = /^\d{4}(-\d{2}(-\d{2})?)?$/;

const ajv = new Ajv({ allErrors: true, strict: false });
const seenIds = new Map(); // id -> { filePath, type }
const componentRefs = []; // { filePath, id }
const tagRefs = []; // { filePath, id }
const entities = []; // { filePath, dir, isCollection, tags } — for the cross-cutting tag pass
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
  if (data.date !== undefined) {
    if (typeof data.date !== 'string' || !DATE_RE.test(data.date)) {
      errors.push(
        `${rel(filePath)}: "date" must be a quoted string in YYYY, YYYY-MM, or YYYY-MM-DD format: ${JSON.stringify(data.date)}`
      );
    }
  }
  if (data.tags !== undefined) {
    if (!Array.isArray(data.tags)) {
      errors.push(`${rel(filePath)}: "tags" must be an array of ids`);
    } else {
      const seenTagIds = new Set();
      for (const ref of data.tags) {
        if (typeof ref !== 'string' || !UUID_RE.test(ref)) {
          errors.push(`${rel(filePath)}: invalid tag id ${JSON.stringify(ref)} — must be a UUID (see tags/)`);
        } else {
          const key = ref.toLowerCase();
          if (seenTagIds.has(key)) {
            errors.push(`${rel(filePath)}: duplicate tag id ${ref}`);
          } else {
            seenTagIds.add(key);
          }
          tagRefs.push({ filePath, id: key });
        }
      }
    }
  }
  if (data.components !== undefined) {
    if (!Array.isArray(data.components)) {
      errors.push(`${rel(filePath)}: "components" must be an array of ids`);
    } else {
      for (const ref of data.components) {
        if (typeof ref !== 'string' || !UUID_RE.test(ref)) {
          errors.push(`${rel(filePath)}: invalid component id ${JSON.stringify(ref)} — must be a UUID`);
        } else {
          componentRefs.push({ filePath, id: ref.toLowerCase() });
        }
      }
    }
  }
  if (data.id) {
    if (!UUID_RE.test(data.id)) {
      errors.push(`${rel(filePath)}: "id" is not a valid UUID: ${data.id}`);
    } else {
      const key = data.id.toLowerCase();
      const existing = seenIds.get(key);
      if (existing) {
        errors.push(`${rel(filePath)}: duplicate id ${data.id} (also used by ${rel(existing.filePath)})`);
      } else {
        seenIds.set(key, { filePath, type: data.type });
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
  const isComponentsDir = path.basename(dir).startsWith('_');
  const isRoot = dir === COLLECTIONS_ROOT || dir === TAGS_ROOT;
  if (!isRoot && !isComponentsDir && !files.includes('_collection.yaml')) {
    errors.push(`${rel(dir)}: missing _collection.yaml`);
  }

  for (const f of entityFiles) {
    const filePath = path.join(dir, f);
    const raw = fs.readFileSync(filePath, 'utf8');
    const data = yaml.load(raw);
    validateEntityStructure(filePath, data);

    // `date` must be quoted in the file, not merely parse as a string.
    // validateEntityStructure only sees the parsed value, and a bare
    // `date: 1994-03` parses as a string just fine — so year-month dates
    // silently violated the documented convention while passing validation.
    // 68 files reached main that way before this check existed, via a
    // dumpEntity() gap (fixed in the same PR as this). A bare YYYY-MM-DD
    // would be worse still: that one parses as a Date object.
    const bareDate = raw.match(/^date: (?!["'])(\S.*)$/m);
    if (bareDate) {
      errors.push(
        `${rel(filePath)}: "date" must be quoted — found \`date: ${bareDate[1]}\`, write \`date: "${bareDate[1]}"\` (see collections/CLAUDE.md, "Dates")`
      );
    }

    entities.push({
      filePath,
      dir,
      isCollection: f === '_collection.yaml',
      tags: Array.isArray(data && data.tags)
        ? data.tags.filter((t) => typeof t === 'string').map((t) => t.toLowerCase())
        : [],
    });

    if (f === '_collection.yaml') {
      if (data && data.type !== 'collection') {
        errors.push(`${rel(filePath)}: _collection.yaml must have type: collection`);
      }
    } else if (schema && data && data.attributes !== undefined) {
      const valid = schema(data.attributes);
      if (!valid) {
        for (const err of schema.errors) {
          // Ajv's raw text for these two is unactionable at this scale — it
          // says "must NOT have additional properties" without naming which
          // one. Name it, and point at the file that decides.
          let detail;
          if (err.keyword === 'additionalProperties') {
            detail = `attributes has undeclared key "${err.params.additionalProperty}" — fix the typo, or declare it in the governing template.schema.json if it genuinely belongs`;
          } else if (err.keyword === 'required') {
            detail = `attributes is missing required key "${err.params.missingProperty}"`;
          } else {
            detail = `attributes${err.instancePath} ${err.message}`;
          }
          errors.push(`${rel(filePath)}: ${detail}`);
        }
      }
    }
  }

  for (const d of dirs) {
    walk(path.join(dir, d), { claudeMdPath, schema });
  }
}

for (const root of [COLLECTIONS_ROOT, TAGS_ROOT]) {
  if (!fs.existsSync(root)) {
    console.error(`No ${rel(root)}/ directory found at ${root}`);
    process.exit(1);
  }
}

walk(COLLECTIONS_ROOT, { claudeMdPath: null, schema: null });
walk(TAGS_ROOT, { claudeMdPath: null, schema: null });

for (const { filePath, id } of componentRefs) {
  if (!seenIds.has(id)) {
    errors.push(`${rel(filePath)}: "components" references unknown id ${id}`);
  }
}

for (const { filePath, id } of tagRefs) {
  const entity = seenIds.get(id);
  if (!entity) {
    errors.push(`${rel(filePath)}: "tags" references unknown id ${id}`);
  } else if (entity.type !== 'tag') {
    errors.push(`${rel(filePath)}: "tags" entry ${id} resolves to a ${entity.type}, not a tag (${rel(entity.filePath)})`);
  }
}

// ---------------------------------------------------------------------------
// Cross-cutting tag invariants.
//
// Referential integrity (above) was never the part that rotted. What rotted
// was *coverage*: the tag namespace was populated during one line's curation
// pass and never applied anywhere else, so for months a franchise search
// resolved ~22,000 Pokémon items down to the 76 that happened to be Funko
// Pops. Nothing here failed, because nothing here was checked.
// ---------------------------------------------------------------------------

const collectionTags = new Map(); // dir -> lowercased tag ids on its _collection.yaml
for (const e of entities) {
  if (e.isCollection) collectionTags.set(e.dir, e.tags);
}

/** Walks from `start` up to the repo root, yielding each collection directory. */
function* ancestryFrom(start) {
  let cur = start;
  while (cur.startsWith(COLLECTIONS_ROOT) || cur.startsWith(TAGS_ROOT)) {
    yield cur;
    cur = path.dirname(cur);
  }
}

// A tag an ancestor collection already carries is a restatement of the
// hierarchy, not new information — see collections/CLAUDE.md ("Tags"):
// "Don't tag both an item and an ancestor collection that already carries
// the same franchise — that duplicate *is* the restatement to avoid."
for (const e of entities) {
  if (e.tags.length === 0) continue;
  // An item's own directory is its parent collection; a collection's own
  // record obviously doesn't duplicate itself, so start one level up.
  const start = e.isCollection ? path.dirname(e.dir) : e.dir;
  for (const dir of ancestryFrom(start)) {
    const owned = collectionTags.get(dir);
    if (!owned) continue;
    for (const t of e.tags) {
      if (owned.includes(t)) {
        errors.push(
          `${rel(e.filePath)}: tag ${t} is already carried by the ancestor collection ${rel(path.join(dir, '_collection.yaml'))} — remove the duplicate (see collections/CLAUDE.md, "Tags")`
        );
      }
    }
  }
}

// A tag entity nothing references is dead weight, and more usefully it's the
// signature of the failure above: the tag got created but never applied.
const referencedTagIds = new Set(tagRefs.map((r) => r.id));
for (const [id, info] of seenIds) {
  if (info.type === 'tag' && !referencedTagIds.has(id)) {
    errors.push(
      `${rel(info.filePath)}: tag entity is referenced by nothing — apply it where it belongs, or drop it. Tags are created at first use, not ahead of it (see collections/CLAUDE.md, "Tags").`
    );
  }
}

// Franchise coverage is *reported, not enforced*. Some lines genuinely have
// no franchise — original-IP plush, a designer brand's own characters — so a
// hard floor would be wrong here. Printing it on every run is what makes a
// regression visible in CI output instead of silent.
const itemEntities = entities.filter((e) => !e.isCollection && e.filePath.startsWith(COLLECTIONS_ROOT));
const gaps = new Map(); // collection dir -> untagged item count
let resolvedCount = 0;
for (const e of itemEntities) {
  let resolved = e.tags.length > 0;
  if (!resolved) {
    for (const dir of ancestryFrom(e.dir)) {
      const owned = collectionTags.get(dir);
      if (owned && owned.length > 0) {
        resolved = true;
        break;
      }
    }
  }
  if (resolved) resolvedCount++;
  else gaps.set(e.dir, (gaps.get(e.dir) || 0) + 1);
}

if (itemEntities.length > 0) {
  const pct = ((100 * resolvedCount) / itemEntities.length).toFixed(1);
  console.log(`tag coverage: ${resolvedCount}/${itemEntities.length} items (${pct}%) resolve a tag from themselves or an ancestor collection`);
  if (gaps.size > 0) {
    const sorted = [...gaps.entries()].sort((a, b) => b[1] - a[1]);
    console.log(`  ${gaps.size} collection(s) hold items with no tag anywhere in their ancestry:`);
    for (const [dir, n] of sorted.slice(0, 15)) console.log(`    ${n.toString().padStart(5)}  ${rel(dir)}`);
    if (sorted.length > 15) console.log(`    ... and ${sorted.length - 15} more`);
    console.log('  (not an error — a line with no franchise is legitimate; check that yours is one)');
  }
  console.log('');
}

if (errors.length > 0) {
  console.error(`✗ ${errors.length} validation error(s):\n`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
} else {
  console.log(`✓ collections/ and tags/ valid (${seenIds.size} entities checked)`);
}
