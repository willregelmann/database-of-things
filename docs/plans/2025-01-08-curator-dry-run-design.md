# Curator Dry Run Feature Design

**Date:** 2025-01-08
**Status:** Validated

## Overview

Add dry run capability to the curator system to validate import scripts without persisting data to the database. This enables safe testing of new curators during the init process and allows manual validation before full imports.

## Goals

1. Validate curator scripts work correctly without database writes
2. Check data structure, relationships, and hierarchy
3. Validate image URLs are accessible (without full download)
4. Provide clear YAML output for human review
5. Save detailed JSON for inspection
6. Integrate with init-curator skill for automatic validation

## Architecture

### Core Components

1. **MockSupabaseClient** (`.curator/lib/dry_run_utils.py`)
   - Implements Supabase client interface
   - Captures all database operations in memory
   - Returns mock responses to satisfy curator logic
   - Provides export methods for captured data

2. **ImageValidator** (in dry_run_utils.py)
   - Validates image URLs without full download
   - Uses HEAD requests to check accessibility
   - Validates content-type headers
   - Reports broken/blocked URLs

3. **DryRunOutput** (in dry_run_utils.py)
   - Builds hierarchical structure from flat data
   - Generates YAML summary for terminal
   - Saves complete JSON file
   - Shows statistics and issues

4. **Template Integration**
   - Add `--dry-run` flag to import scripts
   - Conditionally use MockSupabaseClient
   - Pass dry_run flag through to utilities
   - Generate output at end

## Component Details

### 1. MockSupabaseClient

```python
class MockSupabaseClient:
    """Mock Supabase client that captures operations without executing them."""

    def __init__(self):
        self.entities = []           # Captured entity inserts
        self.relationships = []      # Captured relationship inserts
        self.queries = []            # Captured select queries
        self.deletes = []            # Captured deletes
        self.storage_uploads = []    # Captured storage operations

    def table(self, table_name: str):
        """Return mock table interface."""
        return MockTable(self, table_name)

    def storage(self):
        """Return mock storage interface."""
        return MockStorage(self)
```

**MockTable Implementation:**
- Methods: `.insert()`, `.select()`, `.update()`, `.delete()`, `.eq()`, `.execute()`
- Chains methods by returning self
- `.execute()` captures operation and returns MockResponse
- Generates UUIDs for inserted entities
- Returns empty results for select queries (simulates "not found" for deduplication)

**MockStorage Implementation:**
- Methods: `.from_()`, `.upload()`, `.download()`
- Logs upload operations without saving files
- Returns success responses

### 2. ImageValidator

```python
class ImageValidator:
    """Validates image URLs are accessible without downloading full images."""

    def validate_image(self, url: str) -> dict:
        """
        Validate image URL with HEAD request.

        Returns:
            {
                "url": str,
                "accessible": bool,
                "status_code": int,
                "content_type": str,
                "error": str (if failed)
            }
        """
```

**Validation Logic:**
1. Send HEAD request with 5 second timeout
2. Check status code (200 = success)
3. Verify content-type is image/*
4. If HEAD fails with 405, fallback to GET with byte range
5. Return validation result

**Integration:**
- ImageLocalizer accepts optional `image_validator` parameter
- When provided, calls validator instead of downloading
- Returns mock URLs: `"[would localize from {url}]"`

### 3. DryRunOutput

```python
class DryRunOutput:
    """Generates human-readable YAML and structured JSON from dry run results."""

    def __init__(self, mock_client: MockSupabaseClient, image_results: list):
        self.entities = mock_client.entities
        self.relationships = mock_client.relationships
        self.image_results = image_results

    def build_hierarchy(self) -> dict:
        """Build hierarchical structure from flat entities/relationships."""
        # Group relationships by parent (from_id)
        # Recursively nest children under parents
        # Returns tree structure

    def print_yaml(self, max_entities: int = 3):
        """Print YAML summary to terminal (limited to avoid spam)."""

    def save_json(self, filepath: str):
        """Save complete results to JSON file."""
```

**YAML Output Format:**
```yaml
Dry Run Results:
  Summary:
    Series: 3
    Issues: 10
    Relationships: 13
    Images validated: 8/10 accessible

  Structure (showing first 2 series):
    Marvel Comics:
      Amazing Spider-Man (1963):
        - name: "Amazing Spider-Man #121"
          type: comic
          year: 1973
          writers: ["Gerry Conway"]
          order: 121
          image: ✓ accessible
        - name: "Amazing Spider-Man #122"
          ...

  Image Issues:
    - URL: https://example.com/broken.jpg (404 Not Found)
```

**JSON Output:**
Complete dump of all entities, relationships, and validation results for detailed inspection.

### 4. Import Script Integration

**Template Modifications (import_items.py.template):**

```python
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true',
                       help='Validate import without writing to database')
    args = parser.parse_args()

    # Load configuration
    supabase_url, supabase_key = load_config()

    # Use mock or real client
    if args.dry_run:
        from dry_run_utils import MockSupabaseClient, ImageValidator, DryRunOutput
        supabase = MockSupabaseClient()
        image_validator = ImageValidator()
        print("🔍 DRY RUN MODE - No data will be written to database\n")
    else:
        supabase = create_client(supabase_url, supabase_key)
        image_validator = None

    # Pass dry_run context through
    importer = ItemImporter(
        supabase,
        collection_id,
        dry_run=args.dry_run,
        image_validator=image_validator
    )

    # Run import (captured if dry run)
    results = importer.import_all(items)

    # Generate dry run output
    if args.dry_run:
        output = DryRunOutput(supabase, importer.image_results)
        output.print_yaml()
        output.save_json('dry_run_results.json')
        print(f"\n✓ Dry run complete. Full results saved to dry_run_results.json")
```

**Importer Class Modifications:**
- Accept `dry_run` and `image_validator` parameters
- Pass `image_validator` to `ImageLocalizer` when present
- Track image validation results

**ImageLocalizer Modifications:**
- Accept optional `image_validator` parameter
- When present, validate instead of download:
  ```python
  if self.image_validator:
      result = self.image_validator.validate_image(url)
      return f"[would localize from {url}]", None
  ```

## Init-Curator Integration

After generating curator scripts, ask user:

```
Scripts generated successfully!

Run dry run to validate? (y/n)
```

If yes:
1. Set `FETCH_LIMIT=10` environment variable
2. Run `python3 scripts/fetch_data.py`
3. Run `python3 scripts/import_items.py --dry-run`
4. Display results
5. If errors, allow fixing and re-running
6. If success, proceed to commit

## Error Handling

### Error Scenarios

1. **Fetch fails during dry run**
   - Display error message with full details
   - Don't proceed to import validation
   - Exit with error code 1

2. **API authentication fails**
   - Show clear message: "API keys invalid or missing"
   - Remind to check secrets.env
   - Exit cleanly

3. **Image validation timeout**
   - Mark as "timeout" (not "failed")
   - Don't block entire dry run
   - Report timeouts separately in output

4. **Mock method not implemented**
   - Raise error: "Method X not implemented in MockSupabaseClient"
   - Provides clear feedback for improving mock

### Edge Cases

1. **Deduplication checks** - Mock returns empty results (simulates "not found")
2. **Relationship updates** - Mock tracks both delete and insert operations
3. **Series caching** - Mock's in-memory cache works identically to real client
4. **UUID generation** - Use real UUIDs so relationships link correctly in output

## Configuration

### Defaults

- `FETCH_LIMIT`: 10 (for dry run, configurable)
- `YAML_MAX_ENTITIES`: 3 (max top-level entities shown in terminal)
- `IMAGE_TIMEOUT`: 5 seconds
- `OUTPUT_FILE`: `dry_run_results.json`

### Environment Variables

Existing curator environment variables work unchanged. Dry run uses same configuration but doesn't require valid Supabase credentials (only for fetch script API keys).

## Files to Create

1. `.curator/lib/dry_run_utils.py` - MockSupabaseClient, ImageValidator, DryRunOutput
2. Update `.curator/templates/import_items.py.template` - Add --dry-run flag
3. Update `.claude/skills/init-curator/SKILL.md` - Add dry run prompt

## Files to Update

1. `.curator/lib/image_utils.py` - Accept optional image_validator parameter
2. `.curator/README.md` - Document dry run usage

## Testing Plan

1. Create dry run with Marvel Comics curator (already exists)
2. Run `python3 import_items.py --dry-run` with FETCH_LIMIT=10
3. Verify YAML output shows structure
4. Verify JSON file has complete data
5. Test image validation (accessible and broken URLs)
6. Test init-curator integration
7. Test with Power Rangers curator (hierarchical structure)

## Success Criteria

1. ✅ Dry run completes without database writes
2. ✅ YAML output clearly shows hierarchical structure
3. ✅ Image validation catches broken URLs
4. ✅ JSON file contains all entity/relationship details
5. ✅ Init-curator skill can run dry run automatically
6. ✅ Error messages are clear and actionable
7. ✅ Works with both flat and hierarchical curator structures

## Future Enhancements

- Add `--dry-run-verbose` flag for more detailed output
- Support dry run for relationship update operations
- Add schema validation (check required fields present)
- Performance metrics (fetch time, validation time)
- Diff mode (compare dry run to existing collection)
