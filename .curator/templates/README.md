# Curator Script Templates

This directory contains template scripts for creating new curators. These templates follow all best practices documented in `.curator/README.md`.

## Templates

### fetch_data.py.template

Template for fetching data from external sources (APIs or web scraping).

**Customize**:
- `API_URL` or scraping URL
- `fetch_items()` method for your data source
- `parse_item()` method to extract standardized fields
- Dependencies (add `beautifulsoup4`, `lxml` if web scraping)

### import_items.py.template

Template for importing fetched data into Supabase with all best practices built-in.

**Already includes**:
- ✅ Image localization with thumbnails
- ✅ Embedding generation for semantic search
- ✅ Deduplication via external IDs
- ✅ Proper metadata schema
- ✅ Progress tracking
- ✅ Error handling

**Customize**:
- Entity type (`"card"`, `"toy"`, `"figure"`, etc.)
- External ID field name in `external_ids`
- Domain-specific attributes
- Collection ID (from environment or hardcode)

## Usage

### Option 1: Use /curator:init (Recommended)

```bash
/curator:init "Collection Name"
```

The init skill will generate customized scripts based on your answers.

### Option 2: Copy Templates Manually

```bash
# Create new curator directory
mkdir -p ".curator/curators/My Collection/scripts"

# Copy templates
cp .curator/templates/fetch_data.py.template ".curator/curators/My Collection/scripts/fetch_data.py"
cp .curator/templates/import_items.py.template ".curator/curators/My Collection/scripts/import_items.py"

# Edit scripts and replace CUSTOMIZE comments
vim ".curator/curators/My Collection/scripts/fetch_data.py"
vim ".curator/curators/My Collection/scripts/import_items.py"
```

## What to Customize

Search for `CUSTOMIZE:` comments in the templates. Key areas:

**fetch_data.py:**
- Data source URL
- Pagination or scraping logic
- Field extraction and parsing
- Output data structure

**import_items.py:**
- Entity type
- External ID field names
- Domain-specific attributes
- Collection ID

## Testing

### Testing Your Curator

Before importing to the database, validate your scripts with dry run:

```bash
cd ".curator/curators/Your Collection"
source secrets.env
export FETCH_LIMIT=10
python3 scripts/fetch_data.py
python3 scripts/import_items.py --dry-run
```

This validates:
- ✅ Data source is accessible
- ✅ Parsing logic works correctly
- ✅ Hierarchy structure is correct
- ✅ Image URLs are accessible
- ✅ External IDs are unique

**Review the output:**
- Check YAML hierarchy in terminal
- Inspect `dry_run_results.json` for details
- Fix any issues and re-run

### Additional Testing

1. **Test fetch** with small dataset:
   ```python
   items = fetcher.fetch_items(limit=10)  # Only 10 items
   ```

2. **Inspect fetched data**:
   ```bash
   python3 fetch_data.py
   jq '.[0]' fetched_data.json  # View first item
   ```

3. **Test import** with subset:
   ```python
   items = load_fetched_data()[:10]  # Only import 10
   ```

## See Also

- `.curator/README.md` - Complete best practices documentation
- `.curator/curators/Power Rangers Toys/` - Reference implementation
- `.claude/skills/init-curator/SKILL.md` - Skill that generates from these templates
