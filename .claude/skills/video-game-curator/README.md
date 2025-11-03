# Video Game Curator

Manage your video game collection using the MobyGames API - the most comprehensive video game database.

## Quick Setup

```bash
# 1. Get API key from https://www.mobygames.com/info/api/
#    ($5/month for personal use, $10/month for commercial)

# 2. Add to .env file in project root
echo "MOBY_GAMES_API_KEY=your_api_key_here" >> ../../.env

# 3. Virtual environment is already set up!

# 4. Test API connection
venv/bin/python3 scripts/lib/api_client.py
```

## Quick Start

### Search for Games
```bash
cd scripts
../venv/bin/python3 search_api.py "Pokémon Sword"
../venv/bin/python3 search_api.py "Zelda" --platform 203  # Nintendo Switch only
```

## API Features

**MobyGames API** ($5/month):
- Most comprehensive video game database (since 1979)
- 300,000+ games across 300+ platforms
- **Proper game differentiation**: Separate entries for Sword vs Shield, Red vs Blue
- **Region-specific releases**: NA, EU, JP tracked separately
- **UPC/SKU tracking**: Different editions and versions properly cataloged
- **Scanned box art**: High-quality scans of actual physical game boxes
- Detailed company/developer/publisher information per release
- Perfect for collectibles tracking

**Rate Limits**: 720 requests/hour (~5 seconds between requests)

## Common Platform IDs

- `10` - Game Boy
- `11` - Game Boy Color
- `12` - Game Boy Advance
- `20` - Nintendo DS
- `44` - Nintendo 3DS
- `203` - Nintendo Switch
- `4` - PC
- `142` - Xbox
- `15` - Xbox 360
- `69` - Xbox One
- `289` - Xbox Series X/S
- `7` - PlayStation
- `8` - PlayStation 2
- `16` - PlayStation 3
- `81` - PlayStation 4
- `288` - PlayStation 5

## Next Steps

The skill is ready to use! See `skill.md` for comprehensive documentation on:
- Importing games into your database
- Creating franchises and collections
- Browsing your collection
- Advanced features

## Resources

- **MobyGames API Docs**: https://www.mobygames.com/info/api/
- **Get API Key**: https://www.mobygames.com/info/api/
- **Platform Info**: See skill.md for complete platform list

## Why MobyGames?

MobyGames is the **best API** for tracking physical video game collectibles:

- ✅ **Separate entries for each version**: Pokémon Sword and Pokémon Shield are distinct games
- ✅ **Region-specific releases**: NA, EU, JP releases tracked separately with specific release dates
- ✅ **UPC/SKU tracking**: Different editions and physical versions properly cataloged
- ✅ **Scanned box art**: High-quality scans of actual physical game boxes by country
- ✅ **Publisher/Developer by release**: Tracks who published/developed each regional release
- ✅ **Most comprehensive**: Oldest and largest video game database (since 1979)

Other APIs like RAWG and IGDB combine paired releases (e.g., "Pokémon Sword and Shield") and may not have physical box art scans, making them less suitable for physical collectibles tracking.
