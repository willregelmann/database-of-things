#!/usr/bin/env python3
"""
Import Power Rangers toys from scraped JSON data into the database.

This script imports toy lines (as collections) and individual toys (as action_figures)
with proper hierarchical relationships.
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path

# Database connection settings
CONTAINER_NAME = "supabase_db_database-of-things"
DB_NAME = "postgres"
DB_USER = "postgres"


def exec_sql(sql):
    """Execute SQL in the Supabase PostgreSQL container"""
    cmd = [
        "docker", "exec",
        CONTAINER_NAME,
        "psql",
        "-U", DB_USER,
        "-d", DB_NAME,
        "-t",  # tuples only (no header/footer)
        "-c", sql
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ SQL Error: {result.stderr}")
        return None

    return result.stdout.strip()


def find_entity_by_asst_no(asst_no):
    """Find a toy line collection by asst_no in external_ids"""
    sql = f"""
    SELECT id
    FROM entities
    WHERE type = 'collection'
      AND external_ids->>'asst_no' = '{asst_no}';
    """
    result = exec_sql(sql)
    return result if result else None


def find_toy_by_external_ids_and_name(asst_no, item_no, name):
    """Find a toy by external_ids (asst_no + item_no) and name"""
    # Escape single quotes in name
    safe_name = name.replace("'", "''")

    sql = f"""
    SELECT id
    FROM entities
    WHERE external_ids->>'asst_no' = '{asst_no}'
      AND external_ids->>'item_no' = '{item_no}'
      AND name = '{safe_name}';
    """
    result = exec_sql(sql)
    return result if result else None


def create_entity(entity_type, name, year, country, image_url, external_ids, attributes):
    """Create a new entity"""
    # Escape single quotes
    safe_name = name.replace("'", "''")
    safe_image_url = image_url.replace("'", "''") if image_url else None

    # Build JSON fields
    external_ids_json = json.dumps(external_ids).replace("'", "''")
    attr_json = json.dumps(attributes).replace("'", "''")

    sql = f"""
    INSERT INTO entities (type, name, year, country, image_url, external_ids, attributes)
    VALUES (
        '{entity_type}',
        '{safe_name}',
        {year if year else 'NULL'},
        {f"'{country}'" if country else 'NULL'},
        {f"'{safe_image_url}'" if safe_image_url else 'NULL'},
        '{external_ids_json}'::jsonb,
        '{attr_json}'::jsonb
    )
    RETURNING id;
    """

    result = exec_sql(sql)
    if not result:
        return None

    # Extract just the UUID (first line, strip whitespace)
    # PostgreSQL may return multiple lines with "INSERT 0 1" message
    for line in result.split('\n'):
        line = line.strip()
        # Check if line looks like a UUID (8-4-4-4-12 format)
        if line and '-' in line and len(line) == 36:
            return line

    return None


def update_entity(entity_id, name=None, image_url=None, external_ids=None, attributes=None):
    """Update an existing entity"""
    updates = []

    if name:
        safe_name = name.replace("'", "''")
        updates.append(f"name = '{safe_name}'")

    if image_url:
        safe_image_url = image_url.replace("'", "''")
        updates.append(f"image_url = '{safe_image_url}'")

    if external_ids:
        external_ids_json = json.dumps(external_ids).replace("'", "''")
        updates.append(f"external_ids = '{external_ids_json}'::jsonb")

    if attributes:
        attr_json = json.dumps(attributes).replace("'", "''")
        updates.append(f"attributes = '{attr_json}'::jsonb")

    if not updates:
        return entity_id

    sql = f"""
    UPDATE entities
    SET {', '.join(updates)}
    WHERE id = '{entity_id}';
    """

    exec_sql(sql)
    return entity_id


def create_relationship(from_id, to_id, rel_type):
    """Create a relationship between entities"""
    sql = f"""
    INSERT INTO relationships (from_id, to_id, type)
    VALUES ('{from_id}', '{to_id}', '{rel_type}')
    ON CONFLICT (from_id, to_id, type) DO NOTHING;
    """
    exec_sql(sql)


def import_toys(json_file, series_id, dry_run=False):
    """Import toys from JSON file into database"""

    # Load JSON data
    with open(json_file, 'r') as f:
        data = json.load(f)

    print(f"\n📦 Importing {data['season']} toys")
    print(f"   Series ID: {series_id}")
    print(f"   Toy lines: {len(data['toy_lines'])}")
    print(f"   Total toys: {sum(len(tl['toys']) for tl in data['toy_lines'])}\n")

    if dry_run:
        print("🔍 DRY RUN - No database changes will be made\n")

    # Track stats
    toy_lines_created = 0
    toy_lines_updated = 0
    toys_created = 0
    toys_updated = 0

    # Import each toy line and its toys
    for toy_line in data['toy_lines']:
        asst_no = toy_line['asst_no']
        toy_line_name = f"{asst_no} {toy_line['name']}"

        print(f"\n📦 {toy_line_name}")

        # Build external_ids and attributes
        external_ids = {
            "asst_no": asst_no
        }
        attributes = {
            "manufacturer": "Bandai America"
        }

        if not dry_run:
            # Check if toy line exists
            existing_id = find_entity_by_asst_no(asst_no)

            if existing_id:
                # Update existing
                update_entity(
                    entity_id=existing_id,
                    name=toy_line_name,
                    external_ids=external_ids,
                    attributes=attributes
                )
                toy_line_id = existing_id
                toy_lines_updated += 1
                print(f"   ♻️  Updated toy line collection")
            else:
                # Create new
                toy_line_id = create_entity(
                    entity_type='collection',
                    name=toy_line_name,
                    year=1993,
                    country='US',
                    image_url=None,
                    external_ids=external_ids,
                    attributes=attributes
                )
                toy_lines_created += 1
                print(f"   ✅ Created toy line collection ({toy_line_id})")

            # Link toy line to series
            create_relationship(
                from_id=series_id,
                to_id=toy_line_id,
                rel_type='contains'
            )
        else:
            toy_line_id = "dry-run-id"
            print(f"   Would create/update toy line collection")

        # Import individual toys
        for toy in toy_line['toys']:
            item_no = toy['item_no']
            toy_name = f"{item_no} {toy['name']}"

            # Build external_ids and attributes
            toy_external_ids = {
                "asst_no": asst_no,
                "item_no": item_no
            }
            toy_attributes = {
                "manufacturer": "Bandai America"
            }

            # Determine entity type
            entity_type = "action_figure"

            if not dry_run:
                # Check if toy exists (by external_ids + name)
                existing_toy_id = find_toy_by_external_ids_and_name(
                    asst_no,
                    item_no,
                    toy_name
                )

                if existing_toy_id:
                    # Update existing toy
                    update_entity(
                        entity_id=existing_toy_id,
                        name=toy_name,
                        image_url=toy.get('image_url'),
                        external_ids=toy_external_ids,
                        attributes=toy_attributes
                    )
                    toy_id = existing_toy_id
                    toys_updated += 1
                    print(f"      ♻️  {toy_name}")
                else:
                    # Create new toy
                    toy_id = create_entity(
                        entity_type=entity_type,
                        name=toy_name,
                        year=1993,
                        country='US',
                        image_url=toy.get('image_url'),
                        external_ids=toy_external_ids,
                        attributes=toy_attributes
                    )
                    toys_created += 1
                    print(f"      ✅ {toy_name}")

                # Link toy to toy line
                create_relationship(
                    from_id=toy_line_id,
                    to_id=toy_id,
                    rel_type='contains'
                )
            else:
                print(f"      Would create/update: {toy_name}")

    # Summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)
    print(f"Toy Lines - Created: {toy_lines_created}, Updated: {toy_lines_updated}")
    print(f"Toys - Created: {toys_created}, Updated: {toys_updated}")

    if dry_run:
        print("\n🔍 DRY RUN - No changes were made to the database")


def main():
    parser = argparse.ArgumentParser(description='Import Power Rangers toys from JSON')
    parser.add_argument('json_file', help='JSON file from scrape_season.py')
    parser.add_argument('--series-id', required=True, help='UUID of the Power Rangers series collection')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')

    args = parser.parse_args()

    # Check if JSON file exists
    if not Path(args.json_file).exists():
        print(f"❌ Error: File not found: {args.json_file}")
        sys.exit(1)

    # Import toys
    import_toys(args.json_file, args.series_id, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
