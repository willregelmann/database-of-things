#!/bin/bash

# Import main series Pokemon games with proper rate limiting
# MobyGames requires 1 request/second, and each game import makes 2-3 requests

cd "$(dirname "$0")"

GAMES=(
  "5053:10:Yellow"
  "5515:11:Gold"
  "5426:11:Silver"
  "12055:11:Crystal"
  "8459:12:Ruby"
  "8460:12:Sapphire"
  "17653:12:Emerald"
  "15034:12:FireRed"
  "14757:12:LeafGreen"
)

echo "🎮 Importing Pokemon games from MobyGames..."
echo "This will take a while due to API rate limiting (3 seconds between games)"
echo ""

for entry in "${GAMES[@]}"; do
  IFS=':' read -r game_id platform_id game_name <<< "$entry"
  echo "[$game_name] Importing game ID $game_id for platform $platform_id..."

  ../venv/bin/python3 sync_game.py "$game_id" --platform "$platform_id" 2>&1 | grep -E "^(✅|❌|COMPLETE)"

  echo "  Waiting 3 seconds for rate limit..."
  sleep 3
  echo ""
done

echo "✅ Import complete!"
