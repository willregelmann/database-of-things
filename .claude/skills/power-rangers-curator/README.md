# Power Rangers Curator

Manage your Power Rangers collectibles collection by scraping comprehensive toy data from GRNRngr.com - the definitive Power Rangers toy database.

## Quick Setup

```bash
# Virtual environment is already set up!

# Test the scraper
cd scripts
../venv/bin/python3 scrape_season.py mighty-morphin --dry-run
```

## Data Source

**GRNRngr.com** - Free comprehensive Power Rangers toy guide:
- 233,471 pieces of toy data
- 25+ season toy lines (1993-present)
- Detailed item numbers, prices, release dates, photos, UPCs
- Multiple manufacturers: Hasbro, Bandai America, Playmates, Fisher-Price, Galoob

**Source**: https://www.grnrngr.com/toys/

## Quick Start

### 1. Scrape a Season's Toys

```bash
cd scripts
../venv/bin/python3 scrape_season.py mighty-morphin --output mmpr_toys.json
```

### 2. Import into Database

```bash
# Get series UUID first
cd ../../collectibles-manager/scripts
../venv/bin/python3 search_entities.py --name "Mighty Morphin" --type collection

# Import toys
cd ../../power-rangers-curator/scripts
../venv/bin/python3 import_toys.py mmpr_toys.json --series-id <uuid>
```

## Available Seasons

All 25 Power Rangers seasons are supported:
- `mighty-morphin` - 1993-1996
- `zeo` - 1996
- `turbo` - 1997
- `in-space` - 1998
- (and 21 more...)

See `skill.md` for complete season list.

## Next Steps

The skill is ready to use! See `skill.md` for comprehensive documentation on:
- Scraping all seasons
- Importing toys to database
- Localizing product images
- Advanced features

## Resources

- **Data Source**: https://www.grnrngr.com/toys/
- **Skill Documentation**: See `skill.md`
