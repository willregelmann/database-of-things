#!/bin/bash
# Localize Power Rangers external images to Supabase Storage

set -e

SUPABASE_URL="http://127.0.0.1:54321"
SUPABASE_KEY="sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
TEMP_DIR="/tmp/pr-logos"

mkdir -p "$TEMP_DIR"

echo "Fetching Power Rangers collections with external images..."

# Get all Power Rangers collections with external images
docker exec supabase_db_database-of-things psql -U postgres -d postgres -t -A -F'|' -c "
SELECT id, name, image_url
FROM entities
WHERE type = 'collection'
  AND image_url LIKE 'https://www.grnrngr.com%'
  AND (name LIKE 'Power Rangers%' OR name = 'Mighty Morphin Power Rangers')
ORDER BY name;
" | while IFS='|' read -r entity_id name image_url; do
    echo ""
    echo "Processing: $name"
    echo "  ID: $entity_id"

    # Generate filename from URL
    filename=$(basename "$image_url")
    uuid=$(uuidgen | tr '[:upper:]' '[:lower:]')
    extension="${filename##*.}"

    # Download image
    echo "  Downloading..."
    curl -s "$image_url" -o "$TEMP_DIR/$uuid.$extension"

    if [ ! -s "$TEMP_DIR/$uuid.$extension" ]; then
        echo "  ERROR: Failed to download image"
        continue
    fi

    # Upload original to Supabase Storage
    echo "  Uploading to storage..."
    curl -s -X POST \
      "$SUPABASE_URL/storage/v1/object/images/originals/$uuid.$extension" \
      -H "apikey: $SUPABASE_KEY" \
      -H "Authorization: Bearer $SUPABASE_KEY" \
      -H "Content-Type: image/$extension" \
      --data-binary "@$TEMP_DIR/$uuid.$extension" > /dev/null

    # Update database with new local path
    local_path="/storage/v1/object/public/images/originals/$uuid.$extension"

    echo "  Updating database..."
    docker exec supabase_db_database-of-things psql -U postgres -d postgres -c "
    UPDATE entities
    SET image_url = '$local_path'
    WHERE id = '$entity_id';
    " > /dev/null

    echo "  ✓ Done: $name"

    # Cleanup
    rm "$TEMP_DIR/$uuid.$extension"
done

echo ""
echo "All images localized!"
echo "Now run thumbnail generation: ./scripts/generate-all-thumbnails"

# Cleanup temp directory
rm -rf "$TEMP_DIR"
