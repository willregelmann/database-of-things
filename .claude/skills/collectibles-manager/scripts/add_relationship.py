#!/usr/bin/env python3
"""
Create a relationship between two entities.

Usage:
    python add_relationship.py --from <parent_name> --to <child_name> --type <type> [--attributes <json>]

Examples:
    # Create a contains relationship
    python add_relationship.py --from "Base Set" --to "Charizard 4/102" --type contains

    # Create relationship with ordering
    python add_relationship.py --from "Base Set" --to "Bulbasaur 1/102" --type contains \
                               --attributes '{"order": 1}'

    # Create a variant relationship
    python add_relationship.py --from "Charizard 1st Edition" --to "Charizard" --type variant_of
"""

import argparse
import json
import sys
import subprocess

def find_entity_id(name):
    """Find an entity ID by name."""
    escaped_name = name.replace("'", "''")
    sql = f"SELECT id FROM entities WHERE name = '{escaped_name}' LIMIT 1;"

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-t', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        entity_id = result.stdout.strip()
        if not entity_id:
            return None
        return entity_id
    except subprocess.CalledProcessError:
        return None

def add_relationship(from_name, to_name, rel_type, attributes=None):
    """Create a relationship between two entities."""

    # Find entity IDs
    from_id = find_entity_id(from_name)
    if not from_id:
        print(f"❌ Error: Could not find entity '{from_name}'", file=sys.stderr)
        return False

    to_id = find_entity_id(to_name)
    if not to_id:
        print(f"❌ Error: Could not find entity '{to_name}'", file=sys.stderr)
        return False

    print(f"Found: {from_name} -> {from_id}")
    print(f"Found: {to_name} -> {to_id}")

    # Build the SQL INSERT statement
    attributes_json = json.dumps(attributes) if attributes else '{}'
    escaped_type = rel_type.replace("'", "''")
    escaped_attrs = attributes_json.replace("'", "''")

    sql = f"""
    INSERT INTO relationships (from_id, to_id, type, attributes)
    VALUES ('{from_id}', '{to_id}', '{escaped_type}', '{escaped_attrs}')
    RETURNING id, type;
    """

    # Execute via docker
    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Relationship created successfully!")
        print(f"   {from_name} --[{rel_type}]--> {to_name}")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Error creating relationship:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Create a relationship between entities')
    parser.add_argument('--from', dest='from_name', required=True, help='Parent entity name')
    parser.add_argument('--to', required=True, help='Child entity name')
    parser.add_argument('--type', required=True, help='Relationship type (contains, variant_of, part_of)')
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

    success = add_relationship(
        args.from_name,
        args.to,
        args.type,
        attributes
    )

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
