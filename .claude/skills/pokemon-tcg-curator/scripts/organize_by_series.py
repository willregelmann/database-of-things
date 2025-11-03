#!/usr/bin/env python3
"""
Organize Pokemon TCG sets into series collections.

This script:
1. Finds all unique series from set attributes
2. Creates collection entities for each series
3. Updates relationships: Pokemon TCG → Series → Sets (instead of Pokemon TCG → Sets)
"""

import subprocess
import json
import sys


def exec_sql(sql):
    """Execute SQL and return output"""
    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-d', 'postgres',
        '-t', '-c', sql
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ SQL Error: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout.strip()


def find_pokemon_tcg_root():
    """Find the Pokemon Trading Card Game root collection"""
    sql = """
    SELECT id FROM entities
    WHERE name = 'Pokémon Trading Card Game'
    AND type = 'trading_card_game'
    LIMIT 1;
    """
    result = exec_sql(sql)
    if result:
        return result.strip()
    return None


def get_all_series():
    """Get all unique series with their set counts"""
    sql = """
    SELECT
        attributes->>'series' as series,
        COUNT(*) as set_count
    FROM entities
    WHERE type = 'collection'
    AND attributes ? 'series'
    GROUP BY attributes->>'series'
    ORDER BY series;
    """
    result = exec_sql(sql)
    if not result:
        return []

    series_list = []
    for line in result.split('\n'):
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2 and parts[0]:
                series_list.append({
                    'name': parts[0],
                    'set_count': int(parts[1])
                })
    return series_list


def create_series_collection(series_name, parent_id):
    """Create a collection entity for a series"""
    safe_name = series_name.replace("'", "''")

    # Check if already exists
    check_sql = f"""
    SELECT id FROM entities
    WHERE name = '{safe_name} Series'
    AND type = 'collection'
    LIMIT 1;
    """
    existing = exec_sql(check_sql)
    if existing and existing.strip():
        print(f"  ✓ Series collection already exists: {series_name} Series")
        series_id = existing.split('\n')[0].strip()

        # Get the year for ordering
        year_sql = f"""
        SELECT year FROM entities WHERE id = '{series_id}';
        """
        year_result = exec_sql(year_sql)
        year = None
        if year_result and year_result.strip():
            try:
                year = int(year_result.strip())
            except ValueError:
                pass

        # Ensure relationship to parent exists with order
        relationship_sql = f"""
        INSERT INTO relationships (from_id, to_id, type, \"order\")
        SELECT
          '{parent_id}',
          '{series_id}',
          'contains',
          (SELECT COUNT(*) + 1
           FROM relationships r
           JOIN entities e ON e.id = r.to_id
           WHERE r.from_id = '{parent_id}'
             AND r.type = 'contains'
             AND (e.year < {year if year else 9999}
                  OR (e.year = {year if year else 9999} AND e.name < '{safe_name} Series')))
        ON CONFLICT (from_id, to_id, type) DO UPDATE
        SET \"order\" = EXCLUDED.\"order\";
        """
        exec_sql(relationship_sql)

        # Update year if not set
        update_year_sql = f"""
        UPDATE entities
        SET year = (
          SELECT CAST(SUBSTRING(MIN(sets.attributes->>'releaseDate'), 1, 4) AS INTEGER)
          FROM entities sets
          WHERE sets.type = 'collection'
            AND sets.attributes->>'series' = '{safe_name}'
            AND sets.attributes ? 'releaseDate'
        )
        WHERE id = '{series_id}'
          AND year IS NULL;
        """
        exec_sql(update_year_sql)

        return series_id

    # Get the year from earliest set in this series
    year_sql = f"""
    SELECT CAST(SUBSTRING(MIN(attributes->>'releaseDate'), 1, 4) AS INTEGER)
    FROM entities
    WHERE type = 'collection'
      AND attributes->>'series' = '{safe_name}'
      AND attributes ? 'releaseDate';
    """
    year_result = exec_sql(year_sql)
    year = None
    if year_result and year_result.strip():
        try:
            year = int(year_result.strip())
        except ValueError:
            pass

    # Create new series collection with year
    if year:
        insert_sql = f"""
        INSERT INTO entities (type, name, year)
        VALUES ('collection', '{safe_name} Series', {year})
        RETURNING id;
        """
    else:
        insert_sql = f"""
        INSERT INTO entities (type, name)
        VALUES ('collection', '{safe_name} Series')
        RETURNING id;
        """

    result = exec_sql(insert_sql)
    if not result:
        return None

    # Extract just the UUID (first line, strip whitespace)
    series_id = result.split('\n')[0].strip()
    if year:
        print(f"  ✅ Created: {series_name} Series ({year})")
    else:
        print(f"  ✅ Created: {series_name} Series")

    # Link to parent (Pokemon TCG) with order based on year
    relationship_sql = f"""
    INSERT INTO relationships (from_id, to_id, type, \"order\")
    SELECT
      '{parent_id}',
      '{series_id}',
      'contains',
      (SELECT COUNT(*) + 1
       FROM relationships r
       JOIN entities e ON e.id = r.to_id
       WHERE r.from_id = '{parent_id}'
         AND r.type = 'contains'
         AND (e.year < {year if year else 9999}
              OR (e.year = {year if year else 9999} AND e.name < '{safe_name} Series')))
    ON CONFLICT (from_id, to_id, type) DO UPDATE
    SET \"order\" = EXCLUDED.\"order\";
    """
    exec_sql(relationship_sql)

    return series_id


def reparent_sets_to_series(series_name):
    """Move all sets from Pokemon TCG directly to their series collection"""
    safe_name = series_name.replace("'", "''")

    # Get series collection ID
    series_sql = f"""
    SELECT id FROM entities
    WHERE name = '{safe_name} Series'
    AND type = 'collection'
    LIMIT 1;
    """
    series_id_result = exec_sql(series_sql)
    if not series_id_result or not series_id_result.strip():
        print(f"  ❌ Could not find series collection: {series_name} Series")
        return 0

    series_id = series_id_result.strip()

    # Get Pokemon TCG root ID
    tcg_root_id = find_pokemon_tcg_root()
    if not tcg_root_id:
        print("  ❌ Could not find Pokemon TCG root")
        return 0

    # Get all sets in this series
    sets_sql = f"""
    SELECT id, name FROM entities
    WHERE type = 'collection'
    AND attributes->>'series' = '{safe_name}'
    ORDER BY name;
    """
    sets_result = exec_sql(sets_sql)
    if not sets_result:
        return 0

    set_count = 0
    for line in sets_result.split('\n'):
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 2:
                set_id = parts[0]
                set_name = parts[1]

                # Remove old relationship (TCG → Set)
                delete_sql = f"""
                DELETE FROM relationships
                WHERE from_id = '{tcg_root_id}'
                AND to_id = '{set_id}'
                AND type = 'contains';
                """
                exec_sql(delete_sql)

                # Create new relationship (Series → Set)
                insert_sql = f"""
                INSERT INTO relationships (from_id, to_id, type)
                VALUES ('{series_id}', '{set_id}', 'contains')
                ON CONFLICT DO NOTHING;
                """
                exec_sql(insert_sql)
                set_count += 1

    return set_count


def main():
    print("🎴 Organizing Pokemon TCG sets by series...\n")

    # Find Pokemon TCG root
    tcg_root_id = find_pokemon_tcg_root()
    if not tcg_root_id:
        print("❌ Could not find 'Pokémon Trading Card Game' collection")
        sys.exit(1)

    print(f"✓ Found Pokemon TCG root: {tcg_root_id}\n")

    # Get all series
    all_series = get_all_series()
    if not all_series:
        print("❌ No series found")
        sys.exit(1)

    print(f"📊 Found {len(all_series)} series:\n")

    total_sets = 0
    for series in all_series:
        print(f"📁 {series['name']} ({series['set_count']} sets)")

        # Create series collection
        series_id = create_series_collection(series['name'], tcg_root_id)
        if not series_id:
            print(f"  ❌ Failed to create series collection")
            continue

        # Reparent sets
        moved = reparent_sets_to_series(series['name'])
        print(f"  ↪️  Moved {moved} sets to series")
        total_sets += moved
        print()

    print(f"\n✅ Complete! Organized {total_sets} sets into {len(all_series)} series")


if __name__ == '__main__':
    main()
