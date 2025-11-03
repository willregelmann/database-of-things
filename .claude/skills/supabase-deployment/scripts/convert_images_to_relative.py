#!/usr/bin/env python3
"""
Convert image URLs from localhost absolute paths to portable relative paths.

This makes the database portable across environments (local, staging, production).
Clients prepend the Supabase project URL to these relative paths.

Usage:
    python convert_images_to_relative.py [--dry-run]

Examples:
    # Preview changes
    python convert_images_to_relative.py --dry-run

    # Apply changes
    python convert_images_to_relative.py
"""

import argparse
import subprocess
import sys

CONTAINER_NAME = "supabase_db_database-of-things"


def exec_sql(sql):
    """Execute SQL in the database"""
    cmd = [
        "docker", "exec", CONTAINER_NAME,
        "psql", "-U", "postgres", "-d", "postgres",
        "-t", "-c", sql
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ SQL Error: {result.stderr}", file=sys.stderr)
        return None

    return result.stdout.strip()


def get_localhost_images_count():
    """Count images with localhost URLs"""
    sql = """
    SELECT COUNT(*)
    FROM entities
    WHERE image_url LIKE 'http://127.0.0.1%'
       OR image_url LIKE 'http://localhost%';
    """

    result = exec_sql(sql)
    return int(result.strip()) if result else 0


def convert_to_relative(dry_run=False):
    """Convert localhost URLs to relative paths"""

    print("🔍 Checking for localhost image URLs...")
    count = get_localhost_images_count()

    if count == 0:
        print("✅ No localhost URLs found - all images are already relative or external")
        return True

    print(f"📦 Found {count} images with localhost URLs\n")

    if dry_run:
        print("🔍 DRY RUN - Preview of changes:\n")

        # Show sample conversions
        sql = """
        SELECT
            id,
            name,
            image_url,
            REGEXP_REPLACE(
                image_url,
                '^https?://(127\.0\.0\.1|localhost)(:[0-9]+)?/storage/v1/object/public/',
                ''
            ) as new_url
        FROM entities
        WHERE image_url LIKE 'http://127.0.0.1%'
           OR image_url LIKE 'http://localhost%'
        LIMIT 5;
        """

        result = exec_sql(sql)
        print(result)
        print(f"\n... and {count - 5} more\n")
        print(f"🔍 DRY RUN: Would convert {count} image URLs to relative paths")

    else:
        print("🔄 Converting URLs to relative paths...")

        # Convert URLs using regex to strip the localhost prefix
        sql = """
        UPDATE entities
        SET image_url = REGEXP_REPLACE(
            image_url,
            '^https?://(127\.0\.0\.1|localhost)(:[0-9]+)?/storage/v1/object/public/',
            ''
        )
        WHERE image_url LIKE 'http://127.0.0.1%'
           OR image_url LIKE 'http://localhost%';
        """

        exec_sql(sql)

        # Verify conversion
        remaining = get_localhost_images_count()
        converted = count - remaining

        print(f"✅ Successfully converted {converted} image URLs to relative paths")

        if remaining > 0:
            print(f"⚠️  Warning: {remaining} URLs could not be converted")
            return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Convert localhost image URLs to relative paths for deployment'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without applying them')

    args = parser.parse_args()

    success = convert_to_relative(args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
