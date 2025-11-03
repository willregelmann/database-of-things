#!/usr/bin/env python3
"""
Import all Power Rangers seasons
"""
import subprocess
import sys

FRANCHISE_ID = "d183e3a9-4eb7-40a5-b264-526b9a03ec30"

# Season definitions: (json_file, series_name, year)
SEASONS = [
    ("zeo_toys.json", "Power Rangers Zeo", 1996),
    ("turbo_toys.json", "Power Rangers Turbo", 1997),
    ("in_space_toys.json", "Power Rangers in Space", 1998),
    ("lost_galaxy_toys.json", "Power Rangers Lost Galaxy", 1999),
    ("lightspeed_rescue_toys.json", "Power Rangers Lightspeed Rescue", 2000),
    ("time_force_toys.json", "Power Rangers Time Force", 2001),
    ("wild_force_toys.json", "Power Rangers Wild Force", 2002),
    ("ninja_storm_toys.json", "Power Rangers Ninja Storm", 2003),
    ("dino_thunder_toys.json", "Power Rangers Dino Thunder", 2004),
    ("spd_toys.json", "Power Rangers S.P.D.", 2005),
    ("mystic_force_toys.json", "Power Rangers Mystic Force", 2006),
    ("operation_overdrive_toys.json", "Power Rangers Operation Overdrive", 2007),
    ("jungle_fury_toys.json", "Power Rangers Jungle Fury", 2008),
    ("rpm_toys.json", "Power Rangers RPM", 2009),
    ("samurai_toys.json", "Power Rangers Samurai", 2011),
    ("megaforce_toys.json", "Power Rangers Megaforce", 2013),
    ("dino_charge_toys.json", "Power Rangers Dino Charge", 2015),
    ("ninja_steel_toys.json", "Power Rangers Ninja Steel", 2017),
    ("beast_morphers_toys.json", "Power Rangers Beast Morphers", 2019),
    ("dino_fury_toys.json", "Power Rangers Dino Fury", 2021),
    ("cosmic_fury_toys.json", "Power Rangers Cosmic Fury", 2023),
]


def exec_sql(sql):
    """Execute SQL command"""
    cmd = [
        "docker", "exec", "supabase_db_database-of-things",
        "psql", "-U", "postgres", "-d", "postgres",
        "-t", "-c", sql
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"SQL Error: {result.stderr}", file=sys.stderr)
        return None
    return result.stdout.strip()


def create_series(name, year):
    """Create a series entity and link to franchise"""
    safe_name = name.replace("'", "''")

    # Create series
    sql = f"""
    INSERT INTO entities (type, name, year, country)
    VALUES ('collection', '{safe_name}', {year}, 'US')
    ON CONFLICT DO NOTHING
    RETURNING id;
    """
    result = exec_sql(sql)

    if not result:
        # Series might already exist, try to find it
        sql = f"SELECT id FROM entities WHERE name = '{safe_name}' AND type = 'collection';"
        result = exec_sql(sql)

    if not result:
        return None

    series_id = result.strip().split('\n')[0].strip()

    # Link to franchise
    sql = f"""
    INSERT INTO relationships (from_id, to_id, type)
    VALUES ('{FRANCHISE_ID}', '{series_id}', 'contains')
    ON CONFLICT DO NOTHING;
    """
    exec_sql(sql)

    return series_id


def import_season(json_file, series_id, series_name):
    """Import toys for a season"""
    print(f"\n{'='*70}")
    print(f"Importing {series_name}")
    print(f"{'='*70}")

    cmd = [
        "python3", "import_toys.py",
        json_file,
        "--series-id", series_id
    ]

    result = subprocess.run(cmd, cwd="/home/will/Projects/database-of-things/.claude/skills/power-rangers-curator/scripts")
    return result.returncode == 0


def main():
    print("\n" + "="*70)
    print("POWER RANGERS BULK IMPORT")
    print("="*70)
    print(f"\nImporting {len(SEASONS)} seasons\n")

    successful = 0
    failed = []

    for json_file, series_name, year in SEASONS:
        print(f"\n{series_name} ({year})")
        print("-" * 50)

        # Create series
        print(f"Creating series entity...")
        series_id = create_series(series_name, year)

        if not series_id:
            print(f"❌ Failed to create series")
            failed.append(series_name)
            continue

        print(f"✅ Series created/found: {series_id}")

        # Import toys
        if import_season(json_file, series_id, series_name):
            successful += 1
            print(f"✅ Import successful")
        else:
            print(f"❌ Import failed")
            failed.append(series_name)

    # Summary
    print("\n\n" + "="*70)
    print("BULK IMPORT COMPLETE")
    print("="*70)
    print(f"✅ Successful: {successful}/{len(SEASONS)}")

    if failed:
        print(f"❌ Failed: {len(failed)}")
        for name in failed:
            print(f"   - {name}")
    else:
        print("🎉 All seasons imported successfully!")


if __name__ == '__main__':
    main()
