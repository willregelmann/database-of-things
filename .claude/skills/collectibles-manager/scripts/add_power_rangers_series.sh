#!/bin/bash
# Add all Power Rangers series to the franchise

FRANCHISE_ID="9712daa1-0351-4f3d-9895-65fc08b2e533"

# Power Rangers series in chronological order
declare -a SERIES=(
  "Power Rangers Zeo|1996"
  "Power Rangers Turbo|1997"
  "Power Rangers in Space|1998"
  "Power Rangers Lost Galaxy|1999"
  "Power Rangers Lightspeed Rescue|2000"
  "Power Rangers Time Force|2001"
  "Power Rangers Wild Force|2002"
  "Power Rangers Ninja Storm|2003"
  "Power Rangers Dino Thunder|2004"
  "Power Rangers S.P.D.|2005"
  "Power Rangers Mystic Force|2006"
  "Power Rangers Operation Overdrive|2007"
  "Power Rangers Jungle Fury|2008"
  "Power Rangers RPM|2009"
  "Power Rangers Samurai|2011"
  "Power Rangers Megaforce|2013"
  "Power Rangers Dino Charge|2015"
  "Power Rangers Ninja Steel|2017"
  "Power Rangers Beast Morphers|2019"
  "Power Rangers Dino Fury|2021"
  "Power Rangers Cosmic Fury|2023"
)

for series in "${SERIES[@]}"; do
  IFS='|' read -r name year <<< "$series"
  echo "Adding: $name ($year)"
  
  # Add collection entity
  python3 add_entity.py \
    --type collection \
    --name "$name" \
    --year "$year" \
    --country US \
    --attributes '{"franchise": "Power Rangers", "media_type": "tv_series"}'
  
  echo ""
done

echo "✅ All Power Rangers series added!"
