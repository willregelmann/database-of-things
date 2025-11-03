#!/usr/bin/env python3
"""
Import all Power Rangers seasons from GRNRngr.com

This script scrapes and imports toys from all Power Rangers seasons.
"""

import subprocess
import time
import sys

# Season slug to series name mapping
SEASONS = {
    "mighty-morphin": {"name": "Mighty Morphin Power Rangers", "id": "7cd7e02b-2acd-4f36-aa5c-800ff45427c4"},
    "zeo": {"name": "Power Rangers Zeo", "id": "c57cd8f7-d7f3-4c7a-9ccf-89f150a60d82"},
    "turbo": {"name": "Power Rangers Turbo", "id": "cb3ab28c-cd0a-4b60-b278-ed2ff949a5a2"},
    "in-space": {"name": "Power Rangers in Space", "id": "6ff99122-cdf9-46e0-a205-79c5a2088f03"},
    "lost-galaxy": {"name": "Power Rangers Lost Galaxy", "id": "a6d38f3d-5637-4d6b-a430-3c89f315e619"},
    "lightspeed-rescue": {"name": "Power Rangers Lightspeed Rescue", "id": "73498711-f8ac-40d7-a3b1-ccfd5e0d6724"},
    "time-force": {"name": "Power Rangers Time Force", "id": "fc52b242-96bb-4367-b65f-65c4c6d802c6"},
    "wild-force": {"name": "Power Rangers Wild Force", "id": "7d46470b-8e94-47de-9071-f8829a662cdc"},
    "ninja-storm": {"name": "Power Rangers Ninja Storm", "id": "9dc77bc7-f6a0-4626-9eb7-5c453501f00c"},
    "dino-thunder": {"name": "Power Rangers Dino Thunder", "id": "7427cd82-c77e-4d6f-a5db-e53d599cd46f"},
    "spd": {"name": "Power Rangers S.P.D.", "id": "e1d6b66b-4d86-4de2-a92c-36779fcd3797"},
    "mystic-force": {"name": "Power Rangers Mystic Force", "id": "149b8f6e-62f2-4b36-b306-679939e994d7"},
    "operation-overdrive": {"name": "Power Rangers Operation Overdrive", "id": "4b558ad9-7016-4a5a-9b5e-f9b22e031d1c"},
    "jungle-fury": {"name": "Power Rangers Jungle Fury", "id": "86e11f7d-8b4f-4ee6-a9a9-abe5768139e4"},
    "rpm": {"name": "Power Rangers RPM", "id": "1acba66e-3547-4689-8d2b-b89b632edbf2"},
    "samurai": {"name": "Power Rangers Samurai", "id": "c6180e3f-b8dd-4a2c-968e-990a9e35da83"},
    "megaforce": {"name": "Power Rangers Megaforce", "id": "9d2accb1-8883-432f-87a7-852dc352542e"},
    "dino-charge": {"name": "Power Rangers Dino Charge", "id": "7f9f7d5f-0838-4d97-995d-25d65a8995b6"},
    "ninja-steel": {"name": "Power Rangers Ninja Steel", "id": "7d66a09a-2fe6-432c-bf5a-f391b09f0125"},
    "beast-morphers": {"name": "Power Rangers Beast Morphers", "id": "319c0c01-b920-4368-9770-52faab612610"},
    "dino-fury": {"name": "Power Rangers Dino Fury", "id": "74b26678-6a34-4160-aa29-77b61121dc8e"},
    "cosmic-fury": {"name": "Power Rangers Cosmic Fury", "id": "f508d100-cd1e-45eb-bdcc-cd7efd0da27e"},
}


def run_command(cmd, description):
    """Run a shell command and return result"""
    print(f"\n{'='*70}")
    print(f"{description}")
    print(f"{'='*70}")

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False

    print(result.stdout)
    return True


def main():
    print("\n" + "="*70)
    print("POWER RANGERS SEASONS BATCH IMPORT")
    print("="*70)
    print(f"\nImporting {len(SEASONS)} Power Rangers seasons")
    print(f"This will take approximately {len(SEASONS) * 2} minutes\n")

    # Track stats
    successful = 0
    failed = []

    # Skip Mighty Morphin (already imported)
    seasons_to_import = {k: v for k, v in SEASONS.items() if k != "mighty-morphin"}

    for i, (slug, info) in enumerate(seasons_to_import.items(), 1):
        series_name = info["name"]
        series_id = info["id"]

        print(f"\n\n{'#'*70}")
        print(f"# [{i}/{len(seasons_to_import)}] {series_name}")
        print(f"{'#'*70}\n")

        # Step 1: Scrape
        json_file = f"{slug.replace('-', '_')}_toys.json"
        scrape_cmd = f"../venv/bin/python3 scrape_season.py {slug} --output {json_file}"

        if not run_command(scrape_cmd, f"Scraping {series_name}"):
            failed.append((slug, "scraping failed"))
            continue

        # Brief pause between scrape and import
        time.sleep(1)

        # Step 2: Import
        import_cmd = f"python3 import_toys.py {json_file} --series-id {series_id}"

        if not run_command(import_cmd, f"Importing {series_name}"):
            failed.append((slug, "import failed"))
            continue

        successful += 1

        # Pause between seasons to avoid overwhelming the system
        if i < len(seasons_to_import):
            print(f"\n⏸️  Pausing 2 seconds before next season...")
            time.sleep(2)

    # Final summary
    print("\n\n" + "="*70)
    print("BATCH IMPORT COMPLETE")
    print("="*70)
    print(f"✅ Successful: {successful}/{len(seasons_to_import)}")

    if failed:
        print(f"❌ Failed: {len(failed)}")
        for slug, reason in failed:
            print(f"   - {slug}: {reason}")
    else:
        print("🎉 All seasons imported successfully!")


if __name__ == '__main__':
    main()
