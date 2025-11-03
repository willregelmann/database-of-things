#!/usr/bin/env python3
"""
Search for entities by name or type.

Usage:
    python search_entities.py [--name <pattern>] [--type <type>] [--limit <n>]

Examples:
    # Search for entities with "Charizard" in name
    python search_entities.py --name Charizard

    # Find all collections
    python search_entities.py --type collection

    # Search with limit
    python search_entities.py --name Pokemon --limit 5
"""

import argparse
import sys
import subprocess

def search_entities(name_pattern=None, entity_type=None, limit=50):
    """Search for entities."""

    conditions = []

    if name_pattern:
        # Use ILIKE for case-insensitive search
        escaped_pattern = name_pattern.replace("'", "''")
        conditions.append(f"name ILIKE '%{escaped_pattern}%'")

    if entity_type:
        escaped_type = entity_type.replace("'", "''")
        conditions.append(f"type = '{escaped_type}'")

    where_clause = " AND ".join(conditions) if conditions else "TRUE"

    sql = f"""
    SELECT id, type, name, year, country, image_url
    FROM entities
    WHERE {where_clause}
    ORDER BY name
    LIMIT {limit};
    """

    # Execute via docker
    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if '(0 rows)' in result.stdout:
            print("No entities found matching criteria")
            return True

        print("🔍 Search Results:\n")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Error searching entities:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Search for entities')
    parser.add_argument('--name', help='Search by name (case-insensitive partial match)')
    parser.add_argument('--type', help='Filter by entity type')
    parser.add_argument('--limit', type=int, default=50, help='Maximum results (default: 50)')

    args = parser.parse_args()

    if not args.name and not args.type:
        print("❌ Error: Please provide --name and/or --type", file=sys.stderr)
        sys.exit(1)

    success = search_entities(args.name, args.type, args.limit)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
