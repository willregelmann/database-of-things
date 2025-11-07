#!/usr/bin/env python3
"""Automated test of discovery session with pre-scripted responses."""

import os
import sys
from pathlib import Path
from unittest.mock import patch
from io import StringIO

# Add curator to path
sys.path.insert(0, str(Path(__file__).parent))

from curator.discovery import DiscoverySession
from curator.storage import CuratorStorage
from supabase import create_client
from rich.console import Console

console = Console()


def run_automated_discovery():
    """Run discovery session with automated responses."""

    # Get credentials
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env.local")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not all([anthropic_key, supabase_url, supabase_key]):
        console.print("[red]Error: Missing credentials in .env.local[/]")
        return

    # Create Supabase client
    supabase = create_client(supabase_url, supabase_key)

    # Power Rangers Toys collection ID
    collection_id = "cf968bae-4353-4e54-95b1-87f41e5f9994"
    curator_name = "Power Rangers Toys"

    # Pre-scripted responses that answer Claude's discovery questions
    automated_responses = [
        # Response 1: What type of items?
        """Power Rangers action figures and toys from all series (1993-present).
        This includes 189 toy lines spanning 22 different Power Rangers series,
        from Mighty Morphin through Cosmic Fury. Each toy line is numbered
        (e.g., '2200 Mighty Morphin Power Rangers') and contains multiple products.""",

        # Response 2: Data sources
        """Primary data sources would be:
        1. RangerWiki (https://powerrangers.fandom.com) for series information
        2. Manufacturer catalogs (Bandai America product numbers and details)
        3. Manual entry for rare or custom items

        Each toy already has manufacturer product numbers (2200, 2201, etc.)
        and series associations.""",

        # Response 3: Organization structure
        """The collection has a non-hierarchical graph structure:
        - 'Power Rangers Toys' is the parent collection
        - Each toy line belongs to BOTH 'Power Rangers Toys' AND its specific series
        - For example: '2993 5-inch Triple Action Turbo Rangers' has two parents:
          1. Power Rangers Toys (for browsing all toys)
          2. Power Rangers Turbo (for browsing toys from that series)

        This dual-parent structure is already set up in the database.""",

        # Response 4: Important metadata
        """Key attributes for each toy line:
        - Manufacturer product number (e.g., 2200, 2201) - stored in name
        - Series association (which Power Rangers series)
        - Year of release (if known)
        - Images (currently series logos, but could add product photos)
        - Product description/contents
        - Scale (5-inch, 8-inch, deluxe, etc.)

        Deduplication: Use product number as unique identifier.
        Toy lines with same product number but different series are actually
        the same physical product, just cross-referenced.""",

        # Response 5: Update frequency and import strategy
        """The curator should actively import missing toy lines:
        - Scrape RangerWiki for each of the 22 Power Rangers series
        - Extract toy line information (product numbers, names, descriptions)
        - Automatically create new collection entities for missing toy lines
        - Link them to both 'Power Rangers Toys' AND their specific series
        - Download and store images from RangerWiki

        Run weekly to backfill the collection with vintage toys.
        The goal is to get from 189 toy lines to 300+ (there are many missing).

        Also validate existing data and flag issues for manual review.""",

        # Response 6: Ready to generate
        "done"
    ]

    response_index = 0

    # Patch built-in input function to return automated responses
    def mock_input(prompt=""):
        nonlocal response_index
        if response_index >= len(automated_responses):
            return "done"

        response = automated_responses[response_index]
        response_index += 1

        # Display what we're "typing"
        console.print(f"[bold blue]You:[/] {response[:100]}{'...' if len(response) > 100 else ''}")
        console.print()

        return response

    # Run discovery with mocked input
    console.print("\n[bold cyan]🤖 Starting Automated Discovery Session[/]\n")
    console.print(f"[dim]Collection: {curator_name}[/]")
    console.print(f"[dim]Collection ID: {collection_id}[/]\n")

    try:
        with patch('builtins.input', side_effect=mock_input):
            session = DiscoverySession(
                curator_name=curator_name,
                collection_id=collection_id,
                anthropic_key=anthropic_key,
                supabase_client=supabase
            )

            artifacts = session.run()

        # Save artifacts
        console.print("\n[bold green]📝 Saving artifacts...[/]\n")

        # Check if artifacts were generated
        if not artifacts.get("plan"):
            console.print("[red]Error: No plan was generated (JSON parsing may have failed)[/]")
            console.print("[yellow]Check the raw response file for details[/]")
            return None

        storage = CuratorStorage()
        storage.create_curator_directory(curator_name)
        storage.save_plan(curator_name, artifacts["plan"])
        storage.save_scripts(curator_name, artifacts["scripts"])

        # Save config with collection_id
        config = artifacts.get("config", {})
        config["collection_id"] = collection_id
        storage.save_config(curator_name, config)

        # Save to database
        console.print("[bold green]💾 Saving to database...[/]\n")
        supabase.table("curators").insert({
            "name": curator_name,
            "collection_id": collection_id,
            "config": config
        }).execute()

        console.print(f"[bold green]✨ Success![/]")
        console.print(f"\nCurator saved to: .curator/curators/{curator_name}/")
        console.print(f"Run with: [bold]curator run \"{curator_name}\"[/]")

        # Show what was generated
        console.print("\n[bold]Generated Files:[/]")
        curator_dir = Path(f".curator/curators/{curator_name}")
        for file in sorted(curator_dir.rglob("*")):
            if file.is_file():
                console.print(f"  • {file.relative_to(curator_dir)}")

        return artifacts

    except Exception as e:
        console.print(f"\n[red]Error during discovery: {e}[/]")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_automated_discovery()
