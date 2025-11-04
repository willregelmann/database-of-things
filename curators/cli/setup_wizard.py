"""
Interactive setup wizard for creating new curator agents.

Guides users through creating a curator with:
- Collection name and type
- Base prompt/instructions
- API credentials
- Initial memory setup
"""

from typing import Optional, Dict, Any
from pathlib import Path
import json

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

console = Console()


def run_setup_wizard() -> Dict[str, Any]:
    """
    Run the interactive setup wizard.

    Returns:
        Curator configuration dict
    """
    console.print(
        Panel.fit(
            "[bold cyan]Welcome to the Curator Setup Wizard![/bold cyan]\n\n"
            "This wizard will guide you through creating a new curator agent.\n"
            "Curators autonomously discover, scrape, and import collectibles.",
            title="🎨 Setup Wizard",
            border_style="cyan",
        )
    )
    console.print()

    # Step 1: Basic Information
    curator_id = Prompt.ask(
        "[cyan]Curator ID[/cyan] (lowercase, no spaces, e.g., 'pokemon-tcg')",
        default=None,
    )

    collection_name = Prompt.ask(
        "[cyan]Collection Name[/cyan] (human-readable, e.g., 'Pokémon TCG')",
        default=curator_id.replace("-", " ").title(),
    )

    collection_type = Prompt.ask(
        "[cyan]Collection Type[/cyan]",
        choices=["cards", "figures", "toys", "games", "comics", "other"],
        default="cards",
    )

    # Step 2: Base Prompt
    console.print("\n[bold yellow]📝 Base Prompt[/bold yellow]")
    console.print(
        "Provide instructions for the curator. This is the foundation of its behavior.\n"
    )

    default_prompt = f"""You are a curator agent for the {collection_name} collection.

Your responsibilities:
1. Discover new items in the {collection_name} collection
2. Scrape data from reliable sources
3. Download and process images
4. Import items into the database with proper metadata
5. Organize items into appropriate subcollections

Be thorough, accurate, and respectful of rate limits."""

    console.print(Panel(default_prompt, title="Default Prompt", border_style="dim"))
    console.print()

    use_default = Confirm.ask("Use default prompt?", default=True)

    if use_default:
        base_prompt = default_prompt
    else:
        console.print("[cyan]Enter your custom prompt (end with Ctrl+D or Ctrl+Z):[/cyan]")
        lines = []
        try:
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass
        base_prompt = "\n".join(lines)

    # Step 3: API Credentials
    console.print("\n[bold yellow]🔑 API Credentials[/bold yellow]")
    console.print("Does this collection require API credentials?\n")

    needs_api = Confirm.ask("Add API credentials?", default=False)

    api_credentials = {}
    if needs_api:
        api_name = Prompt.ask("[cyan]API Name[/cyan] (e.g., 'pokemontcg_api')")
        api_key = Prompt.ask("[cyan]API Key[/cyan]", password=True)
        api_credentials[api_name] = api_key

        add_more = Confirm.ask("Add more credentials?", default=False)
        while add_more:
            api_name = Prompt.ask("[cyan]API Name[/cyan]")
            api_key = Prompt.ask("[cyan]API Key[/cyan]", password=True)
            api_credentials[api_name] = api_key
            add_more = Confirm.ask("Add more credentials?", default=False)

    # Step 4: Initial Memory
    console.print("\n[bold yellow]🧠 Initial Memory[/bold yellow]")
    console.print(
        "You can provide initial memories to help the curator understand the collection.\n"
    )

    initial_memories = []

    add_memory = Confirm.ask("Add initial memory?", default=False)
    while add_memory:
        memory_content = Prompt.ask("[cyan]Memory Content[/cyan]")
        memory_category = Prompt.ask(
            "[cyan]Memory Category[/cyan]",
            choices=[
                "collection_structure",
                "strategy",
                "api_credentials",
                "workflow_pattern",
                "metadata_schema",
            ],
            default="strategy",
        )

        initial_memories.append({"content": memory_content, "category": memory_category})

        add_memory = Confirm.ask("Add another memory?", default=False)

    # Step 5: Schedule
    console.print("\n[bold yellow]⏰ Schedule[/bold yellow]")
    console.print("Configure automatic running schedule (optional).\n")

    enable_schedule = Confirm.ask("Enable automatic schedule?", default=False)

    schedule = None
    if enable_schedule:
        schedule = Prompt.ask(
            "[cyan]Cron Expression[/cyan] (e.g., '0 2 * * *' for daily at 2am)",
            default="0 2 * * *",
        )

    # Build configuration
    config = {
        "curator_id": curator_id,
        "collection_name": collection_name,
        "collection_type": collection_type,
        "base_prompt": base_prompt,
        "api_credentials": api_credentials,
        "initial_memories": initial_memories,
        "schedule": schedule,
        "created_at": "2024-11-03T00:00:00Z",  # Will be set dynamically
    }

    # Step 6: Review and Confirm
    console.print("\n[bold green]✅ Configuration Summary[/bold green]\n")
    console.print(Panel(json.dumps(config, indent=2), title="Curator Config", border_style="green"))
    console.print()

    confirm = Confirm.ask("Save this configuration?", default=True)

    if confirm:
        save_configuration(config)
        console.print(f"\n[bold green]✅ Curator '{curator_id}' created successfully![/bold green]\n")
        console.print(f"[cyan]Next steps:[/cyan]")
        console.print(f"  1. Review configuration: [white]curators/config/curators/{curator_id}.json[/white]")
        console.print(f"  2. Run the curator: [white]curator run {curator_id}[/white]")
        console.print()
    else:
        console.print("\n[yellow]⚠️  Configuration not saved[/yellow]\n")

    return config


def save_configuration(config: Dict[str, Any]) -> None:
    """
    Save curator configuration to file.

    Args:
        config: Curator configuration
    """
    curator_id = config["curator_id"]
    config_dir = Path("curators/config/curators")
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / f"{curator_id}.json"

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    console.print(f"[green]✅ Saved to {config_file}[/green]")
