# NTSC Video Games Curator

Fetch North American (NTSC) video game releases from the MobyGames API and import them into the database.

## Credentials

- `MOBY_GAMES_API_KEY` from `secrets.env`
- Auth: `?api_key={key}` query parameter on every request

## Data Source

MobyGames (https://www.mobygames.com) — comprehensive video game database.

Key endpoints:
- `GET https://api.mobygames.com/v1/games?platform={id}&limit=100&offset={n}&format=normal&api_key={key}` — games for a platform
- `GET https://api.mobygames.com/v1/games/{game_id}?api_key={key}` — full game details (cover art)
- `GET https://api.mobygames.com/v1/games/{game_id}/platforms/{platform_id}?api_key={key}` — platform-specific release info (publisher, year, countries)

## Hierarchy

```
NTSC Video Games (top-level collection — this is COLLECTION_ID)
└── Platform (collection)  e.g. "PlayStation 2", "Nintendo Switch"
    └── Game (video_game)  e.g. "Shadow of the Colossus"
```

## Platform IDs (MobyGames)

| Platform | ID | Platform | ID |
|---|---|---|---|
| NES | 18 | SNES | 12 |
| Nintendo 64 | 9 | GameCube | 20 |
| Wii | 82 | Nintendo 3DS | 101 |
| Nintendo Switch | 203 | Game Boy | 10 |
| Game Boy Color | 11 | Game Boy Advance | 14 |
| Nintendo DS | 44 | PlayStation | 7 |
| PlayStation 2 | 21 | PlayStation 3 | 81 |
| PlayStation 4 | 141 | PlayStation 5 | 145 |
| PSP | 46 | Xbox | 13 |
| Xbox 360 | 69 | Xbox One | 142 |
| Xbox Series | 144 | Genesis | 16 |
| Dreamcast | 8 | DOS | 1 |

## Scope: North American releases only

For each game, check platform release data. Only import games that have a release in:
- United States
- Canada
- Worldwide

Skip games with no North American release entry.

## Entity Schemas

### Platform (type: "collection", category: "video_games")

```json
{
  "name": "PlayStation 2",
  "type": "collection",
  "category": "video_games",
  "source_url": "https://www.mobygames.com/platform/21",
  "external_ids": {
    "mobygames_platform_id": "21"
  },
  "attributes": {
    "region": "North America"
  }
}
```

Platform parent = COLLECTION_ID.

### Game (type: "video_game", category: "video_games")

```json
{
  "name": "Shadow of the Colossus",
  "type": "video_game",
  "category": "video_games",
  "year": 2005,
  "country": "US",
  "language": "en",
  "image_url": "https://www.mobygames.com/images/covers/...",
  "source_url": "https://www.mobygames.com/game/12345",
  "external_ids": {
    "mobygames_game_id": "12345",
    "mobygames_game_platform_id": "12345-21"
  },
  "attributes": {
    "publisher": "Sony Computer Entertainment",
    "developer": "Team Ico"
  },
  "parent": {
    "type": "collection",
    "external_ids": { "mobygames_platform_id": "21" }
  }
}
```

**Cover image**: From `game.sample_cover.image` in the game details response.

**Publisher/Developer**: From the NA release's `companies` array. Role "Published by" → publisher, "Developed by" → developer.

**Year**: From `na_release.release_date[:4]`.

## Rate Limiting

MobyGames free tier: ~360 requests/hour. Wait **1.5 seconds** between each API call. This is strict — hitting the rate limit returns 429 and requires waiting.

For bulk imports, prefer smaller batches (50-100 games) to stay well within limits.

## Import

Platform first, then games in batches of 100 (rate limit makes larger batches slow anyway):

```
entities_upsert(collection_id=COLLECTION_ID, items=[platform_entity])
entities_upsert(collection_id=COLLECTION_ID, items=[...games batch...])
```
