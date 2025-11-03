#!/usr/bin/env python3
"""
Display the hierarchical structure starting from an entity.

Usage:
    python list_hierarchy.py <entity_name> [--max-depth <depth>]

Examples:
    # Show full hierarchy under Pokémon
    python list_hierarchy.py "Pokémon"

    # Show only 2 levels deep
    python list_hierarchy.py "Pokémon" --max-depth 2

    # Show what contains a specific card
    python list_hierarchy.py "Bulbasaur 001/165" --reverse
"""

import argparse
import sys
import subprocess

def list_hierarchy(entity_name, max_depth=None, reverse=False):
    """Display hierarchical structure."""

    escaped_name = entity_name.replace("'", "''")

    # Determine direction
    if reverse:
        # Show what contains this entity (go up the tree)
        sql = f"""
        WITH RECURSIVE hierarchy AS (
          -- Start with the target entity
          SELECT id, name, type, 0 as level, ARRAY[name] as path
          FROM entities
          WHERE name = '{escaped_name}'

          UNION ALL

          -- Recursively get parents (what contains this)
          SELECT e.id, e.name, e.type, h.level + 1, h.path || e.name
          FROM entities e
          JOIN relationships r ON r.from_id = e.id
          JOIN hierarchy h ON r.to_id = h.id
          WHERE r.type = 'contains'
          {"AND h.level < " + str(max_depth - 1) if max_depth else ""}
        )
        SELECT level, name, type
        FROM hierarchy
        ORDER BY level DESC, name;
        """
    else:
        # Show what this entity contains (go down the tree)
        sql = f"""
        WITH RECURSIVE hierarchy AS (
          -- Start with the target entity
          SELECT id, name, type, 0 as level, ARRAY[name] as path
          FROM entities
          WHERE name = '{escaped_name}'

          UNION ALL

          -- Recursively get children (what this contains)
          SELECT e.id, e.name, e.type, h.level + 1, h.path || e.name
          FROM entities e
          JOIN relationships r ON r.to_id = e.id
          JOIN hierarchy h ON r.from_id = h.id
          WHERE r.type = 'contains'
          {"AND h.level < " + str(max_depth - 1) if max_depth else ""}
        )
        SELECT level, name, type
        FROM hierarchy
        ORDER BY level, name;
        """

    # Execute via docker
    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        if not result.stdout.strip() or '(0 rows)' in result.stdout:
            print(f"❌ No entity found with name '{entity_name}'", file=sys.stderr)
            return False

        print(f"{'⬆️  Parents of' if reverse else '⬇️  Hierarchy under'}: {entity_name}\n")

        # Parse and format the output
        lines = result.stdout.strip().split('\n')
        if len(lines) > 2:  # Has results beyond header
            # Print with indentation
            for line in lines:
                if '|' in line and not line.startswith('---'):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3 and parts[0].isdigit():
                        level = int(parts[0])
                        name = parts[1]
                        entity_type = parts[2]
                        indent = "  " * level
                        print(f"{indent}{'└─ ' if level > 0 else ''}{name} ({entity_type})")

        return True
    except subprocess.CalledProcessError as e:
        print("❌ Error querying hierarchy:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description='Display entity hierarchy')
    parser.add_argument('entity_name', help='Name of the entity to start from')
    parser.add_argument('--max-depth', type=int, help='Maximum depth to traverse')
    parser.add_argument('--reverse', action='store_true', help='Show parents instead of children')

    args = parser.parse_args()

    success = list_hierarchy(args.entity_name, args.max_depth, args.reverse)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
