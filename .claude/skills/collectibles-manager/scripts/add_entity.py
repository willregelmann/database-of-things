#!/usr/bin/env python3
"""
Add a new entity to the database.

Usage:
    python add_entity.py --type <type> --name <name> [--year <year>] [--country <country>]
                         [--image-url <image_url>] [--attributes <json>]

Examples:
    # Add a simple entity
    python add_entity.py --type collection --name "Base Set"

    # Add an entity with all fields
    python add_entity.py --type trading_card --name "Charizard 4/102" --year 1999 --country US \
                         --image-url "https://images.example.com/charizard.jpg" \
                         --attributes '{"rarity": "rare", "hp": 120}'
"""

import argparse
import json
import sys
import subprocess

def add_entity(type_val, name, year=None, country=None, image_url=None, attributes=None):
    """Add a new entity to the database."""

    # Build the SQL INSERT statement
    columns = ['type', 'name']
    values = [type_val, name]

    if year is not None:
        columns.append('year')
        values.append(str(year))

    if country is not None:
        columns.append('country')
        values.append(country)

    if image_url is not None:
        columns.append('image_url')
        values.append(image_url)

    # Handle attributes JSONB
    if attributes:
        columns.append('attributes')
        values.append(json.dumps(attributes) if isinstance(attributes, dict) else attributes)

    # Build the SQL query
    columns_str = ', '.join(columns)
    placeholders = ', '.join([f"$${i+1}$$" for i in range(len(values))])

    sql = f"""
    INSERT INTO entities ({columns_str})
    VALUES ({placeholders})
    RETURNING id, type, name, year, country, image_url, attributes;
    """

    # Replace placeholders with actual values (PostgreSQL dollar quoting for safety)
    for i, value in enumerate(values):
        escaped_value = str(value).replace("'", "''")
        sql = sql.replace(f"$${i+1}$$", f"'{escaped_value}'")

    # Execute via docker
    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Entity added successfully!")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Error adding entity:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Add a new entity to the collectibles database')
    parser.add_argument('--type', required=True, help='Entity type (e.g., collection, trading_card, franchise)')
    parser.add_argument('--name', required=True, help='Entity name')
    parser.add_argument('--year', type=int, help='Year (optional)')
    parser.add_argument('--country', help='ISO country code (optional)')
    parser.add_argument('--image-url', help='Image URL or path (optional)')
    parser.add_argument('--attributes', help='JSON attributes (optional)')

    args = parser.parse_args()

    # Parse attributes if provided
    attributes = None
    if args.attributes:
        try:
            attributes = json.loads(args.attributes)
        except json.JSONDecodeError:
            print("❌ Invalid JSON in --attributes", file=sys.stderr)
            sys.exit(1)

    success = add_entity(
        args.type,
        args.name,
        args.year,
        args.country,
        args.image_url,
        attributes
    )

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
