#!/usr/bin/env python3
"""
Delete entities matching specific criteria.

SAFETY: Automatically performs dry-run preview before deletion, requires confirmation.

Usage:
    python delete_entities.py [--type <type>] [--name <pattern>] [--where <sql>] [--dry-run]

Examples:
    # Preview what would be deleted
    python delete_entities.py --type action_figure --dry-run

    # Delete entities with type 'action_figure' and year 1993
    python delete_entities.py --where "type = 'action_figure' AND year = 1993"

    # Delete by name pattern
    python delete_entities.py --name "Unreleased" --type action_figure
"""

import argparse
import sys
import subprocess

def count_matching_entities(where_clause):
    """Count how many entities match the criteria."""
    sql = f"""
    SELECT COUNT(*) as count
    FROM entities
    WHERE {where_clause};
    """

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-t', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    except Exception as e:
        print(f"❌ Error counting entities: {e}", file=sys.stderr)
        return -1

def preview_entities(where_clause, limit=20):
    """Show a preview of entities that will be deleted."""
    sql = f"""
    SELECT id, type, name, year, source_url, external_ids
    FROM entities
    WHERE {where_clause}
    ORDER BY name
    LIMIT {limit};
    """

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error previewing entities: {e.stderr}", file=sys.stderr)
        return None

def delete_entities(where_clause, dry_run=False):
    """Delete entities matching criteria. Returns count of deleted entities."""

    # First, show preview
    total_count = count_matching_entities(where_clause)

    if total_count < 0:
        return False

    if total_count == 0:
        print("✅ No entities match the criteria. Nothing to delete.")
        return True

    print(f"\n🔍 Found {total_count} entities matching criteria:\n")
    preview = preview_entities(where_clause, limit=20)

    if preview:
        print(preview)
        if total_count > 20:
            print(f"... and {total_count - 20} more\n")

    if dry_run:
        print(f"🔍 DRY RUN: Would delete {total_count} entities")
        print("Run without --dry-run to actually delete")
        return True

    # Ask for confirmation
    print(f"\n⚠️  WARNING: This will DELETE {total_count} entities and all their relationships!")
    confirmation = input(f"Type 'DELETE {total_count}' to confirm: ")

    if confirmation != f'DELETE {total_count}':
        print("❌ Deletion cancelled")
        return False

    # Delete entities (relationships cascade automatically)
    sql = f"""
    DELETE FROM entities
    WHERE {where_clause};
    """

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"\n✅ Successfully deleted {total_count} entities")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Error deleting entities:", file=sys.stderr)
        print(e.stderr, file=sys.stderr)
        return False

def build_where_clause(args):
    """Build WHERE clause from command-line arguments."""
    conditions = []

    if args.type:
        escaped_type = args.type.replace("'", "''")
        conditions.append(f"type = '{escaped_type}'")

    if args.name:
        escaped_name = args.name.replace("'", "''")
        conditions.append(f"name ILIKE '%{escaped_name}%'")

    if args.where:
        conditions.append(f"({args.where})")

    if not conditions:
        return None

    return " AND ".join(conditions)

def main():
    parser = argparse.ArgumentParser(
        description='Delete entities from the database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview deletion (dry run)
  python delete_entities.py --type action_figure --dry-run

  # Delete all action_figures from 1993 with no source_url
  python delete_entities.py --where "type = 'action_figure' AND year = 1993 AND source_url IS NULL"

  # Delete entities by name pattern
  python delete_entities.py --name "Unreleased" --type action_figure

  # Custom SQL WHERE clause
  python delete_entities.py --where "external_ids ? 'asst_no' AND type = 'action_figure'"
        """
    )

    parser.add_argument('--type', help='Filter by entity type')
    parser.add_argument('--name', help='Filter by name (case-insensitive partial match)')
    parser.add_argument('--where', help='Custom SQL WHERE clause (advanced)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without deleting')

    args = parser.parse_args()

    # Build WHERE clause
    where_clause = build_where_clause(args)

    if not where_clause:
        print("❌ Error: Please provide --type, --name, or --where", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # Execute deletion
    success = delete_entities(where_clause, dry_run=args.dry_run)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
