#!/usr/bin/env python3
"""
Upload storage bucket files to production Supabase Storage.

This script uploads all files from the local storage bucket to production.
Requires production Supabase credentials.

Usage:
    python upload_storage.py --project-url <url> --service-key <key> [--dry-run]

Examples:
    # Preview what would be uploaded
    python upload_storage.py --project-url https://xxx.supabase.co --service-key sk-xxx --dry-run

    # Upload all files
    python upload_storage.py --project-url https://xxx.supabase.co --service-key sk-xxx
"""

import argparse
import subprocess
import sys
import os
import mimetypes
from pathlib import Path


def get_storage_files():
    """Get list of files in local storage backup"""
    # Check if storage backup exists
    backup_dir = Path("./storage-backup")

    if not backup_dir.exists():
        print("❌ Storage backup directory not found", file=sys.stderr)
        print("   Run ./scripts/storage-backup first to create backup", file=sys.stderr)
        return []

    files = []
    for file_path in backup_dir.rglob("*"):
        if file_path.is_file():
            # Get relative path from backup dir
            rel_path = file_path.relative_to(backup_dir)
            files.append((file_path, str(rel_path)))

    return files


def upload_file(file_path, storage_path, project_url, service_key, dry_run=False):
    """Upload a single file to Supabase Storage"""

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(file_path))
    if not content_type:
        content_type = 'application/octet-stream'

    if dry_run:
        print(f"  Would upload: {storage_path}")
        return True

    # Upload using curl with cache-control header
    # Images are content-addressed by UUID, so safe to cache for 1 year
    upload_url = f"{project_url}/storage/v1/object/images/{storage_path}"
    cache_control = "public, max-age=31536000, immutable"

    cmd = [
        'curl', '-X', 'POST', upload_url,
        '-H', f'apikey: {service_key}',
        '-H', f'Authorization: Bearer {service_key}',
        '-H', f'Content-Type: {content_type}',
        '-H', f'x-upsert: true',
        '-H', f'cache-control: {cache_control}',
        '--data-binary', f'@{file_path}',
        '-s', '-w', '%{http_code}'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Check HTTP status code (should be 200 or 201)
    status_code = result.stdout.strip()[-3:]

    if status_code in ['200', '201']:
        return True
    else:
        print(f"  ❌ Failed to upload {storage_path}: HTTP {status_code}", file=sys.stderr)
        return False


def upload_storage(project_url, service_key, dry_run=False):
    """Upload all storage files to production"""

    print("🔍 Finding storage files...")
    files = get_storage_files()

    if not files:
        print("✅ No files to upload")
        return True

    print(f"📦 Found {len(files)} files\n")

    if dry_run:
        print("🔍 DRY RUN - No files will be uploaded\n")

    success_count = 0
    for file_path, storage_path in files:
        if upload_file(file_path, storage_path, project_url, service_key, dry_run):
            success_count += 1

    if dry_run:
        print(f"\n🔍 DRY RUN: Would upload {success_count}/{len(files)} files")
    else:
        print(f"\n✅ Successfully uploaded {success_count}/{len(files)} files")

        if success_count < len(files):
            print(f"⚠️  Warning: {len(files) - success_count} files failed to upload")
            return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Upload storage files to production Supabase'
    )
    parser.add_argument('--project-url', required=True,
                       help='Production Supabase project URL (e.g., https://xxx.supabase.co)')
    parser.add_argument('--service-key', required=True,
                       help='Production service role key')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview uploads without sending files')

    args = parser.parse_args()

    # Validate project URL
    if not args.project_url.startswith('http'):
        print("❌ Invalid project URL - must start with http:// or https://", file=sys.stderr)
        sys.exit(1)

    success = upload_storage(args.project_url, args.service_key, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
