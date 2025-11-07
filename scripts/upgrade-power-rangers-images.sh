#!/bin/bash
# Upgrade Power Rangers images to high-resolution Logopedia versions

set -e

SUPABASE_URL="http://127.0.0.1:54321"
SUPABASE_KEY="sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
TEMP_DIR="/tmp/pr-logos-hd"

mkdir -p "$TEMP_DIR"

echo "🎨 Upgrading Power Rangers images to high-resolution versions"
echo ""

# Define all series with their high-quality logo URLs
declare -A LOGOS=(
    ["Mighty Morphin Power Rangers"]="https://static.wikia.nocookie.net/logopedia/images/d/d3/Mighty_Morphin_Power_Rangers.svg/revision/latest"
    ["Power Rangers Zeo"]="https://static.wikia.nocookie.net/logopedia/images/3/3b/Power_Rangers_Zeo_Logo.png/revision/latest"
    ["Power Rangers Turbo"]="https://static.wikia.nocookie.net/logopedia/images/c/c1/Power_rangers_turbo_logo.png/revision/latest"
    ["Power Rangers in Space"]="https://static.wikia.nocookie.net/logopedia/images/5/55/Power_Rangers_In_Space_Logo.png/revision/latest"
    ["Power Rangers Lost Galaxy"]="https://static.wikia.nocookie.net/logopedia/images/6/69/Power_Rangers_Lost_Galaxy_Logo.png/revision/latest"
    ["Power Rangers Lightspeed Rescue"]="https://static.wikia.nocookie.net/logopedia/images/2/23/Power_Rangers_Lightspeed_Rescue_Logo.png/revision/latest"
    ["Power Rangers Time Force"]="https://static.wikia.nocookie.net/logopedia/images/9/9d/Power_Rangers_Time_Force_Logo.png/revision/latest"
    ["Power Rangers Wild Force"]="https://static.wikia.nocookie.net/logopedia/images/c/ca/Saban%C2%B4s_Power_Rangers_Wild_Force_Logo.png/revision/latest"
    ["Power Rangers Ninja Storm"]="https://static.wikia.nocookie.net/logopedia/images/3/36/Power_Rangers_Ninja_Storm_Logo.png/revision/latest"
    ["Power Rangers Dino Thunder"]="https://static.wikia.nocookie.net/logopedia/images/3/36/Power_Rangers_Dino_Thunder_Logo.png/revision/latest"
    ["Power Rangers S.P.D."]="https://static.wikia.nocookie.net/logopedia/images/7/7c/Power_Rangers_SPD_Logo.png/revision/latest"
    ["Power Rangers Mystic Force"]="https://static.wikia.nocookie.net/logopedia/images/d/dd/Power_Rangers_Mystic_Force_Logo.png/revision/latest"
    ["Power Rangers Operation Overdrive"]="https://static.wikia.nocookie.net/logopedia/images/b/b2/Power_Rangers_Operation_Overdrive_S15_logo_2007.png/revision/latest"
    ["Power Rangers Jungle Fury"]="https://static.wikia.nocookie.net/logopedia/images/2/2c/Power_Rangers_Jungle_Fury_Logo.png/revision/latest"
    ["Power Rangers RPM"]="https://static.wikia.nocookie.net/logopedia/images/2/27/Power_Rangers_RPM_Logo.png/revision/latest"
    ["Power Rangers Samurai"]="https://static.wikia.nocookie.net/logopedia/images/d/d8/Power_Rangers_Samurai_Logo.png/revision/latest"
    ["Power Rangers Megaforce"]="https://static.wikia.nocookie.net/logopedia/images/3/36/Logo-prm.png/revision/latest"
    ["Power Rangers Dino Charge"]="https://static.wikia.nocookie.net/logopedia/images/c/c6/Dinocharge.png/revision/latest"
    ["Power Rangers Ninja Steel"]="https://static.wikia.nocookie.net/logopedia/images/0/07/Ninjasteellogo2.png/revision/latest"
    ["Power Rangers Beast Morphers"]="https://static.wikia.nocookie.net/logopedia/images/e/e7/Power_Rangers_Beast_Morphers_season2_logo.png/revision/latest"
    ["Power Rangers Dino Fury"]="https://static.wikia.nocookie.net/logopedia/images/f/f4/Power_Rangers_Dino_Fury_logo.png/revision/latest"
    ["Power Rangers Cosmic Fury"]="https://static.wikia.nocookie.net/logopedia/images/6/67/PowerRangersCosmicFury.png/revision/latest"
)

for series_name in "${!LOGOS[@]}"; do
    logo_url="${LOGOS[$series_name]}"

    echo "Processing: $series_name"

    # Get entity ID and old image path
    read entity_id old_image <<< $(docker exec supabase_db_database-of-things psql -U postgres -d postgres -t -A -F' ' -c "
    SELECT id, image_url FROM entities
    WHERE name = '$series_name' AND type = 'collection'
    LIMIT 1;
    ")

    if [ -z "$entity_id" ]; then
        echo "  ⚠️  Not found in database, skipping"
        continue
    fi

    echo "  ID: $entity_id"

    # Generate new UUID and determine extension
    uuid=$(uuidgen | tr '[:upper:]' '[:lower:]')
    if [[ "$logo_url" == *.svg* ]]; then
        extension="svg"
    else
        extension="png"
    fi

    # Download high-res image
    echo "  📥 Downloading high-res logo..."
    curl -s -L "$logo_url" -o "$TEMP_DIR/$uuid.$extension"

    if [ ! -s "$TEMP_DIR/$uuid.$extension" ]; then
        echo "  ❌ Failed to download"
        continue
    fi

    # Delete old image from storage (if local)
    if [[ "$old_image" == /storage/* ]]; then
        old_filename=$(basename "$old_image")
        echo "  🗑️  Removing old image..."
        curl -s -X DELETE \
          "$SUPABASE_URL/storage/v1/object/images/originals/$old_filename" \
          -H "apikey: $SUPABASE_KEY" \
          -H "Authorization: Bearer $SUPABASE_KEY" > /dev/null

        # Remove old thumbnail
        old_thumb="${old_filename%.*}.webp"
        curl -s -X DELETE \
          "$SUPABASE_URL/storage/v1/object/images/thumbnails/$old_thumb" \
          -H "apikey: $SUPABASE_KEY" \
          -H "Authorization: Bearer $SUPABASE_KEY" > /dev/null
    fi

    # Upload new high-res image
    echo "  ⬆️  Uploading high-res image..."
    curl -s -X POST \
      "$SUPABASE_URL/storage/v1/object/images/originals/$uuid.$extension" \
      -H "apikey: $SUPABASE_KEY" \
      -H "Authorization: Bearer $SUPABASE_KEY" \
      -H "Content-Type: image/$extension" \
      --data-binary "@$TEMP_DIR/$uuid.$extension" > /dev/null

    # Update database
    local_path="/storage/v1/object/public/images/originals/$uuid.$extension"
    echo "  💾 Updating database..."
    docker exec supabase_db_database-of-things psql -U postgres -d postgres -c "
    UPDATE entities
    SET image_url = '$local_path',
        thumbnail_url = NULL
    WHERE id = '$entity_id';
    " > /dev/null

    echo "  ✅ Done: $series_name"
    echo ""

    # Cleanup
    rm "$TEMP_DIR/$uuid.$extension"
done

echo "🎨 All images upgraded to high-resolution!"
echo "📸 Now regenerating thumbnails..."
echo ""

# Cleanup temp directory
rm -rf "$TEMP_DIR"

# Regenerate thumbnails for Power Rangers only
cd scripts/thumbnails
node backfill-thumbnails.js --limit 25

echo ""
echo "✨ Complete! All Power Rangers images are now high-resolution."
