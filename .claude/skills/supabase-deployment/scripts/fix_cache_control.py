#!/usr/bin/env python3
"""
Fix cache-control headers on existing Supabase Storage objects.

Uses the S3-compatible API to copy objects to themselves with proper cache-control headers.
This is necessary because Supabase storage defaults to 'no-cache' when files are uploaded
without explicit cache-control settings.

The script uses CopyObject with MetadataDirective='REPLACE' to update just the headers
without re-uploading the file content.

Usage:
    python fix_cache_control.py --access-key <key> --secret-key <key> --endpoint <url> [--dry-run]

To get S3 credentials:
    1. Go to Supabase Dashboard > Storage > S3 Access Keys
    2. Create or use existing S3 access key pair
    3. Endpoint is: https://<project-ref>.supabase.co/storage/v1/s3

Examples:
    # Preview what would be updated
    python fix_cache_control.py --access-key xxx --secret-key xxx --endpoint https://xxx.supabase.co/storage/v1/s3 --dry-run

    # Update all files
    python fix_cache_control.py --access-key xxx --secret-key xxx --endpoint https://xxx.supabase.co/storage/v1/s3
"""

import argparse
import sys

try:
    import boto3
    from botocore.config import Config
except ImportError:
    print("❌ boto3 is required. Install with: pip install boto3", file=sys.stderr)
    sys.exit(1)


# Cache-control value: 1 year (images are content-addressed by UUID, so safe to cache forever)
CACHE_CONTROL = "public, max-age=31536000, immutable"

# Bucket name in Supabase storage
BUCKET_NAME = "images"


def get_s3_client(access_key, secret_key, endpoint_url):
    """Create S3 client configured for Supabase"""
    config = Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}
    )

    return boto3.client(
        's3',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        endpoint_url=endpoint_url,
        region_name='us-east-1',  # Required but not used by Supabase
        config=config
    )


def list_objects(s3_client, bucket_name):
    """List all objects in the bucket"""
    objects = []
    paginator = s3_client.get_paginator('list_objects_v2')

    for page in paginator.paginate(Bucket=bucket_name):
        if 'Contents' in page:
            for obj in page['Contents']:
                objects.append(obj)

    return objects


def get_current_cache_control(s3_client, bucket_name, key):
    """Get current cache-control header for an object"""
    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=key)
        return response.get('CacheControl', 'not-set')
    except Exception as e:
        return f"error: {str(e)}"


def update_cache_control(s3_client, bucket_name, key, dry_run=False):
    """Update cache-control for a single object using copy-in-place"""

    if dry_run:
        current = get_current_cache_control(s3_client, bucket_name, key)
        print(f"  Would update: {key} (current: {current})")
        return True

    try:
        # Get current object metadata to preserve Content-Type
        head_response = s3_client.head_object(Bucket=bucket_name, Key=key)
        content_type = head_response.get('ContentType', 'application/octet-stream')

        # Copy object to itself with new cache-control
        copy_source = {'Bucket': bucket_name, 'Key': key}

        s3_client.copy_object(
            Bucket=bucket_name,
            Key=key,
            CopySource=copy_source,
            CacheControl=CACHE_CONTROL,
            ContentType=content_type,
            MetadataDirective='REPLACE'
        )

        return True

    except Exception as e:
        print(f"  ❌ Failed to update {key}: {e}", file=sys.stderr)
        return False


def fix_cache_control(access_key, secret_key, endpoint_url, dry_run=False):
    """Fix cache-control on all objects in the images bucket"""

    print(f"🔌 Connecting to Supabase S3...")
    s3_client = get_s3_client(access_key, secret_key, endpoint_url)

    print(f"🔍 Listing objects in bucket '{BUCKET_NAME}'...")
    try:
        objects = list_objects(s3_client, BUCKET_NAME)
    except Exception as e:
        print(f"❌ Failed to list objects: {e}", file=sys.stderr)
        print("\nTips:", file=sys.stderr)
        print("  - Verify S3 access key and secret key are correct", file=sys.stderr)
        print("  - Ensure endpoint URL is: https://<project-ref>.supabase.co/storage/v1/s3", file=sys.stderr)
        print("  - Enable S3 access in Supabase Dashboard > Storage > S3 Access Keys", file=sys.stderr)
        return False

    if not objects:
        print("✅ No objects found in bucket")
        return True

    print(f"📦 Found {len(objects)} objects\n")

    if dry_run:
        print("🔍 DRY RUN - No objects will be modified\n")

    print(f"Setting cache-control to: {CACHE_CONTROL}\n")

    success_count = 0
    skip_count = 0

    for obj in objects:
        key = obj['Key']

        # Check if already has correct cache-control (skip if so)
        if not dry_run:
            current = get_current_cache_control(s3_client, BUCKET_NAME, key)
            if current == CACHE_CONTROL:
                skip_count += 1
                continue

        if update_cache_control(s3_client, BUCKET_NAME, key, dry_run):
            success_count += 1

    if dry_run:
        print(f"\n🔍 DRY RUN: Would update {success_count}/{len(objects)} objects")
    else:
        total_processed = success_count + skip_count
        print(f"\n✅ Updated {success_count} objects ({skip_count} already had correct cache-control)")

        if total_processed < len(objects):
            failed = len(objects) - total_processed
            print(f"⚠️  Warning: {failed} objects failed to update")
            return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Fix cache-control headers on Supabase Storage objects'
    )
    parser.add_argument('--access-key', required=True,
                       help='Supabase S3 access key ID')
    parser.add_argument('--secret-key', required=True,
                       help='Supabase S3 secret access key')
    parser.add_argument('--endpoint', required=True,
                       help='Supabase S3 endpoint URL (e.g., https://xxx.supabase.co/storage/v1/s3)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview updates without modifying objects')

    args = parser.parse_args()

    # Validate endpoint URL
    if not args.endpoint.startswith('https://'):
        print("❌ Invalid endpoint URL - must start with https://", file=sys.stderr)
        sys.exit(1)

    if not args.endpoint.endswith('/storage/v1/s3'):
        print("⚠️  Warning: Endpoint should end with /storage/v1/s3", file=sys.stderr)

    success = fix_cache_control(args.access_key, args.secret_key, args.endpoint, args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
