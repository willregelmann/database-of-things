import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import yaml from 'js-yaml';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const COLLECTIONS_ROOT = path.join(REPO_ROOT, 'collections');
const TAGS_ROOT = path.join(REPO_ROOT, 'tags');
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const DATE_RE = /^\d{4}(-\d{2}(-\d{2})?)?$/;

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

// The three entity-envelope shapes are global — unlike a per-category
// `schema.json`, none of them vary by directory, so all three are compiled
// once up front rather than during the walk. Applied by kind: a
// `_collection.yaml` (under either root) gets collection.schema.json; a
// tag entity (under tags/) gets tag.schema.json; anything else under
// collections/ gets item.schema.json.
function loadSchema(name) {
  return JSON.parse(fs.readFileSync(path.join(REPO_ROOT, 'schemas', name), 'utf8'));
}
const validateItemShape = ajv.compile(loadSchema('item.schema.json'));
const validateCollectionShape = ajv.compile(loadSchema('collection.schema.json'));
const validateTagShape = ajv.compile(loadSchema('tag.schema.json'));

const seenIds = new Map(); // id -> { filePath, type }
const componentRefs = []; // { filePath, id }
const tagRefs = []; // { filePath, id }
const entities = []; // { filePath, dir, isCollection, tags } — for the cross-cutting tag pass
const errors = [];

function rel(p) {
  return path.relative(REPO_ROOT, p);
}

function reportEntitySchemaErrors(filePath, validateFn, data) {
  if (validateFn(data)) return;
  for (const err of validateFn.errors) {
    const where = err.instancePath === '' ? '(root)' : err.instancePath;
    const detail =
      err.keyword === 'additionalProperties'
        ? `${where} has undeclared key "${err.params.additionalProperty}"`
        : `${where} ${err.message}`;
    errors.push(`${rel(filePath)}: ${detail}`);
  }
}

// Shared by a top-level entity and each of its `variants[]` — the id/tags/
// components/date bookkeeping is identical for both; only what's *required*
// differs (a variant only strictly needs `id`, checked separately by
// item.schema.json — see validateVariants below), so that part stays out of
// this helper.
function validateIdTagsComponentsDate(filePath, data, context) {
  const prefix = context ? `${context}: ` : '';
  if (data.date !== undefined) {
    if (typeof data.date !== 'string' || !DATE_RE.test(data.date)) {
      errors.push(
        `${rel(filePath)}: ${prefix}"date" must be a quoted string in YYYY, YYYY-MM, or YYYY-MM-DD format: ${JSON.stringify(data.date)}`
      );
    }
  }
  if (data.tags !== undefined) {
    if (!Array.isArray(data.tags)) {
      errors.push(`${rel(filePath)}: ${prefix}"tags" must be an array of ids`);
    } else {
      const seenTagIds = new Set();
      for (const ref of data.tags) {
        if (typeof ref !== 'string' || !UUID_RE.test(ref)) {
          errors.push(`${rel(filePath)}: ${prefix}invalid tag id ${JSON.stringify(ref)} — must be a UUID (see tags/)`);
        } else {
          const key = ref.toLowerCase();
          if (seenTagIds.has(key)) {
            errors.push(`${rel(filePath)}: ${prefix}duplicate tag id ${ref}`);
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
      errors.push(`${rel(filePath)}: ${prefix}"components" must be an array of ids`);
    } else {
      for (const ref of data.components) {
        if (typeof ref !== 'string' || !UUID_RE.test(ref)) {
          errors.push(`${rel(filePath)}: ${prefix}invalid component id ${JSON.stringify(ref)} — must be a UUID`);
        } else {
          componentRefs.push({ filePath, id: ref.toLowerCase() });
        }
      }
    }
  }
  if (data.id) {
    if (!UUID_RE.test(data.id)) {
      errors.push(`${rel(filePath)}: ${prefix}"id" is not a valid UUID: ${data.id}`);
    } else {
      const key = data.id.toLowerCase();
      const existing = seenIds.get(key);
      if (existing) {
        errors.push(`${rel(filePath)}: ${prefix}duplicate id ${data.id} (also used by ${rel(existing.filePath)})`);
      } else {
        seenIds.set(key, { filePath, type: data.type });
      }
    }
  }
}

// A variant's own required id/name (and the "capped at one level" rule) is
// already checked by item.schema.json via reportEntitySchemaErrors — this
// only needs to register each variant's id/tags/components into the same
// catalog-wide bookkeeping a top-level entity gets, so other entities can
// validly reference a variant by id and duplicate ids across the whole
// catalog (not just within one file) get caught.
function validateVariants(filePath, data) {
  if (!Array.isArray(data.variants)) return;
  data.variants.forEach((variant, i) => {
    if (!variant || typeof variant !== 'object') return; // reported by item.schema.json already
    validateIdTagsComponentsDate(filePath, variant, `variants[${i}]`);
  });
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
  validateIdTagsComponentsDate(filePath, data, '');
  validateVariants(filePath, data);
}

// A directory's own schema.json layers on top of what it inherited rather
// than replacing it — a family-level schema.json can recommend an attribute
// (declared but not required) and have that recommendation actually reach
// items in every nested collection, not just ones with no schema.json of
// their own. `properties` merge shallowly (child wins a same-named key) —
// EXCEPT when both parent and child declare an `enum` for the same key, in
// which case the two enums union instead of the child replacing the
// parent's outright. That's what lets e.g. a series-specific rarity sit
// alongside the universal ones inherited from the category, rather than a
// series template having to restate every universal value just to add its
// own. `required` unions (a child can add a requirement, not remove an
// inherited one), and `additionalProperties` takes the child's own value
// when it declares one — which is what makes a "real" series template's
// `additionalProperties: false` still correctly allow an inherited
// recommended key: by the time it's evaluated, that key is already merged
// into `properties`.
function mergeProperty(parentProp, childProp) {
  if (!parentProp) return childProp;
  if (!childProp) return parentProp;
  if (Array.isArray(parentProp.enum) && Array.isArray(childProp.enum)) {
    return { ...parentProp, ...childProp, enum: [...new Set([...parentProp.enum, ...childProp.enum])] };
  }
  // Array-of-enum properties (e.g. "type": {type: array, items: {enum: [...]}})
  // carry their enum inside `items`, not on the property itself — same
  // union logic, one level deeper.
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

function walk(dir, inherited) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = entries.filter((e) => e.isFile()).map((e) => e.name);
  const dirs = entries.filter((e) => e.isDirectory()).map((e) => e.name);

  let { claudeMdPath, schema, schemaJson } = inherited;

  if (files.includes('CLAUDE.md')) {
    claudeMdPath = path.join(dir, 'CLAUDE.md');
  }
  if (files.includes('schema.json')) {
    const schemaPath = path.join(dir, 'schema.json');
    const ownSchemaJson = JSON.parse(fs.readFileSync(schemaPath, 'utf8'));
    schemaJson = mergeAttributesSchema(schemaJson, ownSchemaJson);
    schema = ajv.compile(schemaJson);
  }

  const entityFiles = files.filter((f) => f.endsWith('.yaml') || f.endsWith('.yml'));

  if (entityFiles.length > 0 && !claudeMdPath) {
    errors.push(`${rel(dir)}: contains entity files but has no CLAUDE.md (own or inherited)`);
  }
  // No blanket "must have a schema.json" gate here — a `_collection.yaml` is
  // never checked against one (see below), and a directory that will only
  // ever hold collection records (a family, a publisher-only directory, a
  // tag namespace whose entities never carry `attributes`) genuinely has
  // nothing for one to govern. The real invariant — an item's `attributes`
  // never silently goes unvalidated — is enforced per-file below instead,
  // where it's actually known whether `attributes` is present.
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
    // would be worse still: that one parses as a Date object. Matches any
    // indentation, not just column 0, so a bare date nested under a
    // `variants[]` entry is caught too.
    for (const m of raw.matchAll(/^[ \t]*date: (?!["'])(\S.*)$/gm)) {
      errors.push(
        `${rel(filePath)}: "date" must be quoted — found \`date: ${m[1]}\`, write \`date: "${m[1]}"\` (see collections/CLAUDE.md, "Dates")`
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
      if (data && typeof data === 'object') {
        reportEntitySchemaErrors(filePath, validateCollectionShape, data);
      }
    } else {
      if (data && typeof data === 'object') {
        // Whole-entity shape: id/name required, image/date/tags typed
        // correctly. A tag entity (under tags/) gets tag.schema.json;
        // everything else under collections/ is an item and gets
        // item.schema.json — attributes/variants, including each variant's
        // own id requirement and the one-level nesting cap.
        const isTag = dir === TAGS_ROOT || dir.startsWith(TAGS_ROOT + path.sep);
        reportEntitySchemaErrors(filePath, isTag ? validateTagShape : validateItemShape, data);
      }
      if (data && data.attributes !== undefined && !schema) {
        errors.push(
          `${rel(filePath)}: has "attributes" but no schema.json (own or inherited) exists to validate them against`
        );
      } else if (schema && data && data.attributes !== undefined) {
        const valid = schema(data.attributes);
        if (!valid) {
          for (const err of schema.errors) {
            // Ajv's raw text for these two is unactionable at this scale — it
            // says "must NOT have additional properties" without naming which
            // one. Name it, and point at the file that decides.
            let detail;
            if (err.keyword === 'additionalProperties') {
              detail = `attributes has undeclared key "${err.params.additionalProperty}" — fix the typo, or declare it in the governing schema.json if it genuinely belongs`;
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
  }

  for (const d of dirs) {
    walk(path.join(dir, d), { claudeMdPath, schema, schemaJson });
  }
}

for (const root of [COLLECTIONS_ROOT, TAGS_ROOT]) {
  if (!fs.existsSync(root)) {
    console.error(`No ${rel(root)}/ directory found at ${root}`);
    process.exit(1);
  }
}

walk(COLLECTIONS_ROOT, { claudeMdPath: null, schema: null, schemaJson: null });
walk(TAGS_ROOT, { claudeMdPath: null, schema: null, schemaJson: null });

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
