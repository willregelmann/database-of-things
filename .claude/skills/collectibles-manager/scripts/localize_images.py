#!/usr/bin/env python3
"""
Download external images and store them in Supabase Storage.

This script:
1. Finds all entities with external image URLs (http/https)
2. Downloads each image
3. Uploads to Supabase Storage as <entity_id>.<extension>
4. Updates the entity's image_url to the storage path

Usage:
    python localize_images.py [--dry-run] [--limit <n>]

Examples:
    # Preview what would be downloaded
    python localize_images.py --dry-run

    # Download and store all images
    python localize_images.py

    # Process only first 5 images
    python localize_images.py --limit 5
"""

import argparse
import sys
import subprocess
import urllib.request
import urllib.parse
import os
import tempfile
import mimetypes

def get_entities_with_external_images(limit=None):
    """Get entities that have external image URLs."""
    sql = """
    SELECT id, name, image_url
    FROM entities
    WHERE image_url LIKE 'http%'
    ORDER BY created_at
    """

    if limit:
        sql += f" LIMIT {limit};"
    else:
        sql += ";"

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-t', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        entities = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:
                    entities.append({
                        'id': parts[0],
                        'name': parts[1],
                        'image_url': parts[2]
                    })

        return entities
    except subprocess.CalledProcessError as e:
        print(f"❌ Error querying entities: {e.stderr}", file=sys.stderr)
        return []

def get_file_extension(url):
    """Extract file extension from URL."""
    # Try from URL path
    parsed = urllib.parse.urlparse(url)
    path = parsed.path

    # Get extension from path
    _, ext = os.path.splitext(path)
    if ext:
        return ext.lower()

    # Default to .jpg if no extension found
    return '.jpg'

def download_image(url, entity_id):
    """Download an image and return the temporary file path."""
    try:
        # Set user agent to avoid 403 errors
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            # Get extension from URL or content-type
            ext = get_file_extension(url)

            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_file.write(response.read())
            temp_file.close()

            return temp_file.name, ext
    except Exception as e:
        print(f"  ❌ Error downloading: {e}", file=sys.stderr)
        return None, None

def upload_to_storage(file_path, entity_id, extension):
    """Upload file to Supabase Storage."""
    # Storage path: just the entity ID with extension, no subdirectory
    storage_path = f"{entity_id}{extension}"

    # Determine content type
    content_type, _ = mimetypes.guess_type(file_path)
    if not content_type:
        content_type = 'image/jpeg'

    # Get Supabase API URL and key
    status_cmd = ['bin/supabase', 'status']
    try:
        result = subprocess.run(status_cmd, capture_output=True, text=True, check=True, cwd='/home/will/Projects/database-of-things')

        api_url = None
        service_key = None
        for line in result.stdout.split('\n'):
            if 'API URL:' in line:
                api_url = line.split(':', 1)[1].strip()
            elif 'Secret key:' in line:
                # Use service role key to bypass RLS for administrative uploads
                service_key = line.split(':', 1)[1].strip()

        if not api_url or not service_key:
            print("  ❌ Could not get Supabase credentials", file=sys.stderr)
            return None

        # Upload using curl with service role key (bypasses RLS)
        upload_url = f"{api_url}/storage/v1/object/images/{storage_path}"

        cmd = [
            'curl', '-X', 'POST', upload_url,
            '-H', f'apikey: {service_key}',
            '-H', f'Authorization: Bearer {service_key}',
            '-H', f'Content-Type: {content_type}',
            '--data-binary', f'@{file_path}',
            '-s'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Return relative path (portable across environments)
            return f"/storage/v1/object/public/images/{storage_path}"
        else:
            print(f"  ❌ Upload failed: {result.stderr}", file=sys.stderr)
            return None

    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error uploading: {e.stderr}", file=sys.stderr)
        return None

def update_entity_image_url(entity_id, new_image_url):
    """Update entity's image_url to the storage path."""
    escaped_url = new_image_url.replace("'", "''")

    sql = f"""
    UPDATE entities
    SET image_url = '{escaped_url}'
    WHERE id = '{entity_id}';
    """

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error updating entity: {e.stderr}", file=sys.stderr)
        return False

def localize_images(dry_run=False, limit=None):
    """Main function to localize all external images."""

    print("🔍 Finding entities with external images...")
    entities = get_entities_with_external_images(limit)

    if not entities:
        print("✅ No entities with external images found")
        return True

    print(f"📦 Found {len(entities)} entities with external images\n")

    if dry_run:
        print("🔍 DRY RUN - No changes will be made\n")

    success_count = 0
    for i, entity in enumerate(entities, 1):
        entity_id = entity['id']
        name = entity['name']
        url = entity['image_url']

        print(f"[{i}/{len(entities)}] {name}")
        print(f"  URL: {url}")

        if dry_run:
            ext = get_file_extension(url)
            print(f"  Would save as: images/{entity_id}{ext}")
            success_count += 1
            continue

        # Download image
        print(f"  ⬇️  Downloading...")
        temp_file, ext = download_image(url, entity_id)

        if not temp_file:
            print(f"  ⏭️  Skipping (download failed)")
            continue

        try:
            # Upload to storage
            print(f"  ⬆️  Uploading to storage...")
            storage_path = upload_to_storage(temp_file, entity_id, ext)

            if not storage_path:
                print(f"  ⏭️  Skipping (upload failed)")
                continue

            # Update entity
            print(f"  💾 Updating entity...")
            if update_entity_image_url(entity_id, storage_path):
                print(f"  ✅ Success: {storage_path}")
                success_count += 1
            else:
                print(f"  ⏭️  Skipping (update failed)")

        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

        print()

    if dry_run:
        print(f"🔍 DRY RUN: Would process {success_count}/{len(entities)} images")
    else:
        print(f"✅ Successfully localized {success_count}/{len(entities)} images")

    return True

def main():
    parser = argparse.ArgumentParser(description='Download external images and store in Supabase Storage')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without downloading')
    parser.add_argument('--limit', type=int, help='Limit number of images to process')

    args = parser.parse_args()

    success = localize_images(args.dry_run, args.limit)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
