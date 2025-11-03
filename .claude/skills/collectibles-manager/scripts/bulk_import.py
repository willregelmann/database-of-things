#!/usr/bin/env python3
"""
Bulk import entities and relationships from a JSON file.

Usage:
    python bulk_import.py <json_file>

JSON Format:
    {
      "entities": [
        {
          "name": "Entity Name",
          "type": "entity_type",
          "year": 2023,
          "country": "US",
          "image_url": "https://...",
          "attributes": {"key": "value"}
        }
      ],
      "relationships": [
        {
          "from": "Parent Entity Name",
          "to": "Child Entity Name",
          "type": "contains",
          "attributes": {"order": 1}
        }
      ]
    }

Example:
    python bulk_import.py pokemon_base_set.json
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
        return entity_id if entity_id else None
    except subprocess.CalledProcessError:
        return None

def add_entity(entity):
    """Add a single entity."""
    columns = ['type', 'name']
    values = [entity['type'], entity['name']]

    for optional in ['year', 'country', 'image_url']:
        if optional in entity and entity[optional]:
            columns.append(optional)
            values.append(str(entity[optional]))

    if 'attributes' in entity and entity['attributes']:
        columns.append('attributes')
        values.append(json.dumps(entity['attributes']))

    # Build SQL
    columns_str = ', '.join(columns)
    values_escaped = [str(v).replace("'", "''") for v in values]
    values_str = "', '".join(values_escaped)

    sql = f"INSERT INTO entities ({columns_str}) VALUES ('{values_str}') RETURNING id, name;"

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-t', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error adding {entity['name']}: {e.stderr}", file=sys.stderr)
        return False

def add_relationship(rel):
    """Add a single relationship."""
    from_id = find_entity_id(rel['from'])
    if not from_id:
        print(f"  ⚠️  Skipping relationship: '{rel['from']}' not found", file=sys.stderr)
        return False

    to_id = find_entity_id(rel['to'])
    if not to_id:
        print(f"  ⚠️  Skipping relationship: '{rel['to']}' not found", file=sys.stderr)
        return False

    attributes = json.dumps(rel.get('attributes', {}))
    rel_type = rel['type']
    escaped_type = rel_type.replace("'", "''")
    escaped_attrs = attributes.replace("'", "''")

    sql = f"""
    INSERT INTO relationships (from_id, to_id, type, attributes)
    VALUES ('{from_id}', '{to_id}', '{escaped_type}', '{escaped_attrs}');
    """

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Error adding relationship {rel['from']} -> {rel['to']}: {e.stderr}", file=sys.stderr)
        return False

def bulk_import(json_file):
    """Import entities and relationships from JSON."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {json_file}", file=sys.stderr)
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        return False

    # Import entities first
    entities = data.get('entities', [])
    print(f"📦 Importing {len(entities)} entities...")

    success_count = 0
    for i, entity in enumerate(entities, 1):
        if add_entity(entity):
            success_count += 1
            print(f"  ✅ {i}/{len(entities)}: {entity['name']}")
        else:
            print(f"  ❌ {i}/{len(entities)}: {entity['name']}")

    print(f"\n✅ Imported {success_count}/{len(entities)} entities")

    # Import relationships
    relationships = data.get('relationships', [])
    if relationships:
        print(f"\n🔗 Importing {len(relationships)} relationships...")

        rel_success = 0
        for i, rel in enumerate(relationships, 1):
            if add_relationship(rel):
                rel_success += 1
                print(f"  ✅ {i}/{len(relationships)}: {rel['from']} -> {rel['to']}")

        print(f"\n✅ Imported {rel_success}/{len(relationships)} relationships")

    return True

def main():
    parser = argparse.ArgumentParser(description='Bulk import entities and relationships from JSON')
    parser.add_argument('json_file', help='Path to JSON file')

    args = parser.parse_args()

    success = bulk_import(args.json_file)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
