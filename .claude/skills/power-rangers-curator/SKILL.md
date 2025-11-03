---
name: power-rangers-curator
description: Curate Power Rangers collectibles by scraping toy data from GRNRngr.com. Use when importing Power Rangers toys with item numbers, release dates, retail prices, UPC/barcodes, and photos (233,471 pieces of data from 1993-present).
---

# Power Rangers Curator

## Overview

Curate your Power Rangers collectibles collection by scraping comprehensive toy data from [GRNRngr.com](https://www.grnrngr.com/toys/), the definitive Power Rangers toy database with 233,471 pieces of data.

**Perfect for collectibles tracking**: Detailed item numbers, release dates, retail prices, UPC/barcodes, and photos for every Power Rangers toy from 1993-present.

**Works with**: `collectibles-manager` skill for database operations.

## Data Source

### GRNRngr.com - Power Rangers Toy Guide

- **Free** web resource (no API key required)
- **Most comprehensive** Power Rangers toy database
- 25+ season toy lines from Mighty Morphin through Cosmic Fury
- Multiple manufacturers: Hasbro, Bandai America, Playmates, Fisher-Price, Galoob
- Detailed information:
  - Item numbers (e.g., 2200, 2212)
  - Product names
  - Suggested retail prices (SRP)
  - Release dates
  - UPC/barcodes
  - Product photos
  - Case counts (wholesale distribution)
  - Instruction PDFs

**Source**: https://www.grnrngr.com/toys/

**No API**: Data must be scraped from HTML pages

## Quick Start

The skill manages this hierarchy:
1. **Franchise** (franchise) - "Power Rangers"
2. **Series** (collection) - Individual TV seasons (e.g., "Mighty Morphin Power Rangers", "Power Rangers Zeo")
3. **Toy Lines** (collection) - Product categories within each season (e.g., "2200 Mighty Morphin Power Rangers", "2250 Power Morpher")
4. **Toys** (action_figure / toy) - Individual products (e.g., "Jason Red Ranger", "Power Morpher")

All scripts use web scraping with BeautifulSoup4 and require Python dependencies.

### Setup

The skill uses `requests` and `beautifulsoup4` for web scraping:

```bash
# Create virtual environment
cd .claude/skills/power-rangers-curator
python3 -m venv venv

# Install dependencies
venv/bin/pip install -r requirements.txt
```

**Running scripts**: Use the venv python:
```bash
cd .claude/skills/power-rangers-curator/scripts
../venv/bin/python3 scrape_toys.py --help
```

## Core Operations

### 1. Scrape Season Toy Data

Use `scripts/scrape_season.py` to scrape all toys from a specific Power Rangers season.

**Usage:**
```bash
../venv/bin/python3 scrape_season.py <season_slug> [--dry-run] [--output <file>]
```

**Arguments:**
- `<season_slug>` - URL slug for the season (e.g., "mighty-morphin", "zeo", "turbo")

**Options:**
- `--dry-run` - Preview what would be scraped without saving
- `--output <file>` - Save scraped data to JSON file (default: `<season>_toys.json`)

**What it does:**
1. Fetches the season page from grnrngr.com
2. Parses all toy lines and products
3. Extracts item numbers, names, prices, release dates, photos, UPCs
4. Saves to JSON file for import

**Examples:**
```bash
# Scrape Mighty Morphin toys (preview)
../venv/bin/python3 scrape_season.py mighty-morphin --dry-run

# Scrape and save to file
../venv/bin/python3 scrape_season.py mighty-morphin --output mmpr_toys.json

# Scrape Power Rangers Zeo
../venv/bin/python3 scrape_season.py zeo
```

### 2. Import Scraped Toys

Use `scripts/import_toys.py` to import scraped toy data into the database.

**Usage:**
```bash
../venv/bin/python3 import_toys.py <json_file> --series-id <uuid> [--dry-run]
```

**Arguments:**
- `<json_file>` - JSON file from scrape_season.py
- `--series-id <uuid>` - UUID of the Power Rangers series collection to link toys to

**Options:**
- `--dry-run` - Preview what would be imported without making changes

**Entity structure:**

✅ **Important**: External IDs are stored in the dedicated `external_ids` column (JSONB), NOT nested in `attributes`. Attributes only contain collector-relevant metadata like manufacturer.

**Toy Line Collections** (e.g., "2200 Mighty Morphin Power Rangers"):
- `type`: "collection"
- `name`: Product line name with assortment number prefix
- `year`: Release year
- `country`: "US" (all toys are US releases)
- `image_url`: Initially external URL from grnrngr.com; converted to portable relative path (e.g., `/storage/v1/object/public/images/uuid.jpg`) when localized via `collectibles-manager/localize_images.py`
- `external_ids` (dedicated column):
  - `asst_no`: Assortment/collection number (e.g., "2200")
- `attributes`:
  - `manufacturer`: e.g., "Bandai America"

**Individual Toys** (e.g., "2200 Jason Red Ranger"):
- `type`: "action_figure" or "toy" (based on product category)
- `name`: Product name with item number prefix
- `year`: Release year
- `country`: "US" (all toys are US releases)
- `image_url`: Initially external URL from grnrngr.com; converted to portable relative path (e.g., `/storage/v1/object/public/images/uuid.jpg`) when localized via `collectibles-manager/localize_images.py`
- `attributes`:
  - `manufacturer`: e.g., "Bandai America"
- `external_ids`:
  - `asst_no`: Assortment number (e.g., "2200")
  - `item_no`: Individual item number (e.g., "2200")

**Note**: `asst_no` and `item_no` are often the same for the first items in a toy line (e.g., both "2200") but diverge for later items (e.g., asst_no "2200", item_no "2212").

**Deduplication Strategy**: Unfortunately, multiple toys in early assortments often share the same `item_no` (e.g., Jason, Zack, Billy, Trini, and Kimberly all have item_no "2200"), so deduplication must use **both** `external_ids.item_no` + `name` for uniqueness checking. This allows proper tracking of which items belong to which assortment/collection while avoiding duplicates

**Examples:**
```bash
# Preview import
../venv/bin/python3 import_toys.py mmpr_toys.json \
  --series-id 7cd7e02b-2acd-4f36-aa5c-800ff45427c4 \
  --dry-run

# Import toys
../venv/bin/python3 import_toys.py mmpr_toys.json \
  --series-id 7cd7e02b-2acd-4f36-aa5c-800ff45427c4
```

## Common Workflows

### Import a Complete Season

**Example: Import Mighty Morphin Power Rangers toys**

```bash
# 1. Scrape the season
../venv/bin/python3 scrape_season.py mighty-morphin

# 2. Get series UUID
cd ../../collectibles-manager/scripts
../venv/bin/python3 search_entities.py --name "Mighty Morphin Power Rangers" --type collection

# 3. Import toys
cd ../../power-rangers-curator/scripts
../venv/bin/python3 import_toys.py mighty_morphin_toys.json \
  --series-id <series-uuid-from-step-2>

# 4. Localize images (downloads to local storage and converts to portable paths)
cd ../../collectibles-manager/scripts
../venv/bin/python3 localize_images.py --limit 100
```

**Note**: After localization, image URLs will be converted from external URLs to portable relative paths (e.g., `/storage/v1/object/public/images/uuid.jpg`), making the database fully portable across environments.

### Import All Seasons

```bash
# Scrape all 25 seasons
for season in mighty-morphin zeo turbo in-space lost-galaxy \
              lightspeed-rescue time-force wild-force ninja-storm \
              dino-thunder spd mystic-force operation-overdrive \
              jungle-fury rpm mighty-morphin-2010 samurai megaforce \
              super-megaforce dino-charge dino-super-charge \
              ninja-steel super-ninja-steel beast-morphers \
              dino-fury cosmic-fury; do
  ../venv/bin/python3 scrape_season.py $season
done

# Then import each JSON file with appropriate series UUID
```

## Season URL Slugs

- `mighty-morphin` - Mighty Morphin Power Rangers (1993-1996)
- `zeo` - Power Rangers Zeo (1996)
- `turbo` - Power Rangers Turbo (1997)
- `in-space` - Power Rangers in Space (1998)
- `lost-galaxy` - Power Rangers Lost Galaxy (1999)
- `lightspeed-rescue` - Power Rangers Lightspeed Rescue (2000)
- `time-force` - Power Rangers Time Force (2001)
- `wild-force` - Power Rangers Wild Force (2002)
- `ninja-storm` - Power Rangers Ninja Storm (2003)
- `dino-thunder` - Power Rangers Dino Thunder (2004)
- `spd` - Power Rangers S.P.D. (2005)
- `mystic-force` - Power Rangers Mystic Force (2006)
- `operation-overdrive` - Power Rangers Operation Overdrive (2007)
- `jungle-fury` - Power Rangers Jungle Fury (2008)
- `rpm` - Power Rangers RPM (2009)
- `mighty-morphin-2010` - Mighty Morphin Power Rangers 2010 Re-release
- `samurai` - Power Rangers Samurai (2011)
- `megaforce` - Power Rangers Megaforce (2013)
- `super-megaforce` - Power Rangers Super Megaforce (2014)
- `dino-charge` - Power Rangers Dino Charge (2015)
- `dino-super-charge` - Power Rangers Dino Super Charge (2016)
- `ninja-steel` - Power Rangers Ninja Steel (2017)
- `super-ninja-steel` - Power Rangers Super Ninja Steel (2018)
- `beast-morphers` - Power Rangers Beast Morphers (2019)
- `dino-fury` - Power Rangers Dino Fury (2021)
- `cosmic-fury` - Power Rangers Cosmic Fury (2023)

## Resources

### scripts/
Python scripts for Power Rangers toy operations:
- `scrape_season.py` - Scrape toys from grnrngr.com
- `import_toys.py` - Import scraped toys to database

All scripts support `--help` flag for detailed usage.

## Future Enhancements

Potential additions:
- Automatic image downloading during scraping
- Support for other toy lines (Lightning Collection, Playskool Heroes)
- Related franchises (VR Troopers, BeetleBorgs)
- Instruction PDF downloads
- Secondary market price tracking via eBay integration
- Barcode/UPC scanning for collection management
