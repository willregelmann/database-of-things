"""
Example: Autonomous Elden Ring Curator

This demonstrates the meta-system approach where the curator:
1. Analyzes the source autonomously
2. Generates the necessary scraper code
3. Executes and learns

Compare to: curators/elden_ring_curator.py (330 lines of hand-coded logic)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.autonomous_curator import AutonomousCurator
from dotenv import load_dotenv

load_dotenv()


async def main():
    """Run the autonomous curator on Elden Ring merchandise."""

    print("\n" + "="*70)
    print("AUTONOMOUS CURATOR - ELDEN RING EXAMPLE")
    print("="*70 + "\n")

    # Create curator with minimal instruction
    curator = AutonomousCurator()

    # Phase A: Initialize with minimal user input
    await curator.initialize(
        goal="Import Elden Ring merchandise from Bandai Namco Store",
        source="https://store.bandainamcoent.eu/games/brands/elden-ring/",
        collection_id="c427fd49-97d1-427b-8126-cee2042fef63"  # Existing root collection
    )

    # Full autonomous run: discover → generate → execute
    print("\n" + "="*70)
    print("STARTING AUTONOMOUS RUN")
    print("="*70 + "\n")

    results = await curator.run()

    # Display results
    print("\n" + "="*70)
    print("RESULTS")
    print("="*70 + "\n")
    print(f"Success: {results.get('success', False)}")
    print(f"Summary: {results.get('summary', 'N/A')}")

    if results.get('stats'):
        print(f"\nStatistics:")
        for key, value in results['stats'].items():
            print(f"  {key}: {value}")

    # Show curator status
    print("\n" + "="*70)
    print("CURATOR STATUS")
    print("="*70 + "\n")
    status = curator.status()
    for key, value in status.items():
        print(f"{key}: {value}")

    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
