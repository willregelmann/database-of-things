#!/usr/bin/env python3
"""
Fix cache-control headers on existing Supabase Storage objects using REST API.

This script downloads and re-uploads each file with proper cache-control headers.
Uses the Supabase REST API with service role key (no separate S3 credentials needed).

Note: This approach transfers file content, so it's slower than the S3 CopyObject method.
For ~3000 images at ~100KB average, expect ~30 minutes runtime.

Usage:
    python fix_cache_control_rest.py --project-url <url> --service-key <key> [--dry-run]

Examples:
    # Preview what would be updated
    python fix_cache_control_rest.py --project-url https://xxx.supabase.co --service-key sk-xxx --dry-run

    # Update all files
    python fix_cache_control_rest.py --project-url https://xxx.supabase.co --service-key sk-xxx
"""

import argparse
import sys
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Cache-control value: 1 year (images are content-addressed by UUID, so safe to cache forever)
CACHE_CONTROL = "public, max-age=31536000, immutable"

# Bucket name in Supabase storage
BUCKET_NAME = "images"

# Number of parallel workers
MAX_WORKERS = 5


def list_all_objects(project_url, service_key):
    """List all objects in the images bucket"""
    objects = []

    # List root level
    objects.extend(list_folder_objects(project_url, service_key, ""))

    return objects


def list_folder_objects(project_url, service_key, folder):
    """List objects in a specific folder"""
    url = f"{project_url}/storage/v1/object/list/{BUCKET_NAME}"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json"
    }

    body = {"prefix": folder, "limit": 1000}
    objects = []

    while True:
        response = requests.post(url, headers=headers, json=body)

        if response.status_code != 200:
            print(f"❌ Failed to list objects in '{folder}': {response.text}", file=sys.stderr)
            break

        items = response.json()

        for item in items:
            if item.get('id'):  # It's a file
                full_path = f"{folder}/{item['name']}" if folder else item['name']
                objects.append({
                    'name': full_path,
                    'metadata': item.get('metadata', {}),
                })
            else:  # It's a folder
                subfolder = f"{folder}/{item['name']}" if folder else item['name']
                objects.extend(list_folder_objects(project_url, service_key, subfolder))

        # Check for pagination
        if len(items) < 1000:
            break

        # Paginate using offset
        body['offset'] = body.get('offset', 0) + 1000

    return objects


def get_current_cache_control(obj):
    """Get current cache-control from object metadata"""
    metadata = obj.get('metadata', {})
    return metadata.get('cacheControl', 'not-set')


def update_object_cache_control(project_url, service_key, obj_name, dry_run=False):
    """Download and re-upload a single object with new cache-control"""

    if dry_run:
        return True, "dry-run"

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    # Download the file
    download_url = f"{project_url}/storage/v1/object/{BUCKET_NAME}/{obj_name}"
    download_response = requests.get(download_url, headers=headers)

    if download_response.status_code != 200:
        return False, f"download failed: {download_response.status_code}"

    content = download_response.content
    content_type = download_response.headers.get('Content-Type', 'application/octet-stream')

    # Re-upload with new cache-control
    upload_url = f"{project_url}/storage/v1/object/{BUCKET_NAME}/{obj_name}"
    upload_headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
        "cache-control": CACHE_CONTROL,
    }

    upload_response = requests.post(upload_url, headers=upload_headers, data=content)

    if upload_response.status_code in [200, 201]:
        return True, "updated"
    else:
        return False, f"upload failed: {upload_response.status_code} - {upload_response.text}"


def fix_cache_control(project_url, service_key, dry_run=False):
    """Fix cache-control on all objects in the images bucket"""

    print(f"🔍 Listing objects in bucket '{BUCKET_NAME}'...")

    try:
        objects = list_all_objects(project_url, service_key)
    except Exception as e:
        print(f"❌ Failed to list objects: {e}", file=sys.stderr)
        return False

    if not objects:
        print("✅ No objects found in bucket")
        return True

    print(f"📦 Found {len(objects)} objects\n")

    if dry_run:
        print("🔍 DRY RUN - No objects will be modified\n")

    print(f"Setting cache-control to: {CACHE_CONTROL}\n")

    # Filter objects that need updating
    needs_update = []
    skip_count = 0

    for obj in objects:
        current = get_current_cache_control(obj)
        if current == CACHE_CONTROL:
            skip_count += 1
        else:
            needs_update.append(obj)
            if dry_run:
                print(f"  Would update: {obj['name']} (current: {current})")

    if dry_run:
        print(f"\n🔍 DRY RUN: Would update {len(needs_update)}/{len(objects)} objects")
        print(f"   ({skip_count} already have correct cache-control)")
        return True

    if not needs_update:
        print(f"✅ All {len(objects)} objects already have correct cache-control")
        return True

    print(f"📤 Updating {len(needs_update)} objects ({skip_count} already correct)...\n")

    success_count = 0
    fail_count = 0
    start_time = time.time()

    # Process with progress updates
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(update_object_cache_control, project_url, service_key, obj['name'], False): obj
            for obj in needs_update
        }

        for i, future in enumerate(as_completed(futures), 1):
            obj = futures[future]
            try:
                success, msg = future.result()
                if success:
                    success_count += 1
                else:
                    fail_count += 1
                    print(f"  ❌ {obj['name']}: {msg}")
            except Exception as e:
                fail_count += 1
                print(f"  ❌ {obj['name']}: {e}")

            # Progress update every 50 files
            if i % 50 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (len(needs_update) - i) / rate
                print(f"  Progress: {i}/{len(needs_update)} ({success_count} ok, {fail_count} failed) - ETA: {remaining:.0f}s")

    elapsed = time.time() - start_time
    print(f"\n✅ Updated {success_count} objects in {elapsed:.1f}s")

    if fail_count > 0:
        print(f"⚠️  Warning: {fail_count} objects failed to update")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Fix cache-control headers on Supabase Storage objects (REST API version)'
    )
    parser.add_argument('--project-url', required=True,
                       help='Supabase project URL (e.g., https://xxx.supabase.co)')
    parser.add_argument('--service-key', required=True,
                       help='Supabase service role key')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview updates without modifying objects')

    args = parser.parse_args()

    # Validate project URL
    if not args.project_url.startswith('https://'):
        print("❌ Invalid project URL - must start with https://", file=sys.stderr)
        sys.exit(1)

    success = fix_cache_control(args.project_url, args.service_key, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
