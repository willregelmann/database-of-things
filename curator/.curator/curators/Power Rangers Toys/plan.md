# Power Rangers Toys Curator - Implementation Plan

## Overview
Autonomous curator to discover and import Power Rangers toy lines from RangerWiki, growing the collection from 189 to 300+ items through weekly backfill operations.

## Collection Structure
- **Graph-based dual-parent system**: Each toy line belongs to both "Power Rangers Toys" (main collection) AND its specific series collection
- **Product numbers** (2200, 2201, etc.) serve as unique identifiers
- **22 Power Rangers series** from Mighty Morphin (1993) to Cosmic Fury (2023)

## Data Sources
1. **RangerWiki** (https://powerrangers.fandom.com)
   - Series pages with merchandise sections
   - Pattern: `/wiki/{Series_Name}` → look for toy/merchandise tables
   - Extract: product numbers, names, descriptions, release years, images

2. **Manual validation** for edge cases and quality control

## Workflow

### 1. Discovery Phase (fetch_rangerwiki.py)
- Iterate through 22 known Power Rangers series
- Scrape merchandise/toy sections from each series wiki page
- Parse HTML tables and infoboxes for toy line data
- Extract product numbers using regex patterns: `(\d{4})` 
- Download images to local storage (`images/` directory)
- Output structured JSON for import

### 2. Import Phase (import_toylines.py)
- Read scraped data from JSON
- Check existing database for duplicate product numbers
- Create new item entities for missing toy lines
- Ensure parent collections exist (create series collections if needed)
- Link items to both "Power Rangers Toys" AND series collection
- Store metadata: year, description, scale, image paths

### 3. Validation Phase (validate_collection.py)
- Scan for orphaned items (missing parent relationships)
- Detect duplicate product numbers with conflicting data
- Flag missing critical metadata (product number, series)
- Verify image file integrity
- Generate issue report for manual review

## Deduplication Strategy
- **Primary key**: Manufacturer product number (extracted from name)
- **Merge rule**: Same product number = same physical toy
- **Cross-reference**: Toys sold under multiple series get multiple parent links
- **No fuzzy matching**: Exact product number match only

## Metadata Schema
```json
{
  "product_number": "2200",
  "series": "Mighty Morphin Power Rangers",
  "year": "1993",
  "scale": "5-inch",
  "description": "Action figure with accessories",
  "manufacturer": "Bandai America",
  "image_url": "https://...",
  "image_local": "images/2200.jpg",
  "source": "rangerwiki",
  "scraped_date": "2024-01-15"
}
```

## Update Schedule
- **Weekly runs**: Every Sunday at 2 AM
- **Incremental discovery**: Only import new/missing items
- **Validation**: Run after each import
- **Manual review**: Check flagged issues weekly

## Success Metrics
- Grow from 189 → 300+ toy lines within 8-12 weeks
- <5% duplicate rate
- >95% of items have complete metadata
- All items have correct dual-parent structure

## Risk Mitigation
- **Rate limiting**: 2-second delay between RangerWiki requests
- **Dry run mode**: Preview imports before committing
- **Backup**: SQLite backup before bulk operations
- **Logging**: Detailed logs for debugging and auditing