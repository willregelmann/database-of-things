"""Interactive discovery session for curator design."""

from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
import json
import logging

console = Console()
logger = logging.getLogger(__name__)


class DiscoverySession:
    """Interactive session to design a curator through conversation.

    This uses Claude to conduct a Socratic discovery process, helping
    the user articulate their collection structure, data sources, and
    workflows. The result is a plan document and generated scripts.
    """

    def __init__(
        self,
        curator_name: str,
        collection_id: str,
        anthropic_key: str,
        supabase_client = None
    ):
        """Initialize discovery session.

        Args:
            curator_name: Name of curator being created
            collection_id: UUID of collection entity (or None to create)
            anthropic_key: Anthropic API key
            supabase_client: Supabase client for inspecting current state
        """
        self.curator_name = curator_name
        self.collection_id = collection_id
        self.client = Anthropic(api_key=anthropic_key)
        self.db = supabase_client
        self.conversation_history = []
        self.artifacts = {
            "plan": None,
            "scripts": [],
            "secrets": [],
            "config": {}
        }
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt for discovery agent."""
        return """You are helping a user design a curator agent for their collectibles database.

Your goal: Through Socratic questioning, understand their collection and help them design an autonomous curator that ACTIVELY IMPORTS DATA.

**CRITICAL: All curators are for DATA IMPORT by default.** The curator should fetch items from external sources and add them to the database.

Key areas to explore:
1. **Collection Scope** - What items belong in this collection? How are they organized?
2. **Data Sources** - Where does data come from? APIs? Web scraping? Manual entry?
   - Focus on HOW to fetch/scrape this data programmatically
   - What URLs, endpoints, or APIs are available?
3. **Organization** - Should items be in subcollections? How should they be hierarchical?
4. **Metadata** - What attributes are important? What makes items unique?
5. **Import Strategy** - How should new items be added?
   - Bulk import vs incremental?
   - What's the deduplication key (unique identifier)?
6. **Update Frequency** - How often should the curator run to import new items?

Ask thoughtful questions. Listen to their answers. Build understanding incrementally.

When you have sufficient understanding, generate:

1. **Plan Document** (Markdown)
   - Collection structure
   - Data sources and HOW to access them
   - Import workflow (fetch → deduplicate → import)
   - Deduplication strategy

2. **Scripts** (Python) - FOCUS ON IMPORT
   - fetch_data.py - Scrape/fetch items from external source
   - import_items.py - Import fetched items into database
   - validate_collection.py - Optional validation/audit

3. **Secrets List**
   - Required API keys
   - Validation instructions

The curator will have access to execute_script() tool to run these scripts during execution.

Use tools to inspect the current database state when helpful.

Important: Generate COMPLETE, WORKING scripts. Don't use pseudocode or placeholders.
Scripts should be IMPORT-FOCUSED - scraping data and adding items to the collection.
"""

    def run(self) -> Dict[str, Any]:
        """Run interactive discovery session.

        Returns:
            Dictionary with plan, scripts, secrets, and config
        """
        console.print(Panel.fit(
            f"[bold]Discovery Session: {self.curator_name}[/]\n\n"
            "I'll help you design this curator through conversation.\n"
            "Type 'done' when you're ready to generate the plan.",
            title="🤖 Curator Discovery",
            border_style="blue"
        ))

        # Initialize conversation
        self._add_message("assistant", self._get_initial_message())

        # Conversation loop
        while not self._is_discovery_complete():
            # Show assistant message
            last_message = self.conversation_history[-1]
            if last_message["role"] == "assistant":
                console.print()
                console.print(Markdown(last_message["content"]))
                console.print()

            # Get user input
            user_input = console.input("[bold blue]You:[/] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["done", "finish", "complete"]:
                console.print("\n[yellow]Generating plan and scripts...[/]\n")
                self._generate_artifacts()
                break

            # Add to conversation
            self._add_message("user", user_input)

            # Get Claude response
            response = self._get_claude_response()
            self._add_message("assistant", response)

        # Show results
        self._display_results()

        return self.artifacts

    def _get_initial_message(self) -> str:
        """Get initial discovery message."""
        return f"""Hi! I'm here to help you design the **{self.curator_name}** curator.

Let's start with the basics:

**What type of items will this collection contain?**

For example:
- Trading cards from a specific game?
- Action figures from a franchise?
- Comic books from a publisher?
- Something else entirely?

Tell me about what you're collecting!"""

    def _add_message(self, role: str, content: str):
        """Add message to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    def _get_claude_response(self) -> str:
        """Get Claude's response to the conversation.

        Returns:
            Assistant's response text
        """
        try:
            # Use higher max_tokens for artifact generation
            max_tokens = 8192 if any("generate:" in msg["content"].lower() or "synthesis" in msg["content"].lower() for msg in self.conversation_history[-3:]) else 4096

            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=max_tokens,
                system=self.system_prompt,
                messages=self.conversation_history
            )

            # Extract text from response
            text_blocks = [
                block.text for block in response.content
                if hasattr(block, "text")
            ]
            return "\n\n".join(text_blocks)

        except Exception as e:
            logger.error(f"Error getting Claude response: {e}")
            return "I'm having trouble connecting. Let's try again."

    def _is_discovery_complete(self) -> bool:
        """Check if discovery is complete.

        Returns:
            True if artifacts have been generated
        """
        return self.artifacts["plan"] is not None

    def _generate_artifacts(self):
        """Generate plan, scripts, and config from conversation.

        This sends a final message to Claude asking it to synthesize
        the conversation into concrete artifacts.
        """
        synthesis_prompt = """Based on our conversation, please generate:

1. A comprehensive plan document (Markdown format)
2. Python scripts for data fetching and management (CONCISE but complete)
3. List of required secrets/API keys
4. Configuration settings (dedup threshold, schedule, etc)

IMPORTANT: Keep scripts CONCISE. Focus on core logic. Use helper functions.
Aim for 100-200 lines per script max. Prioritize the 2-3 most important scripts.

Format your response as JSON:

```json
{
  "plan": "# Plan Document\\n\\n...",
  "scripts": [
    {
      "filename": "fetch_data.py",
      "code": "import requests\\n..."
    }
  ],
  "secrets": [
    {
      "key": "API_KEY_NAME",
      "description": "What this key is for",
      "validation_url": "https://..."
    }
  ],
  "config": {
    "dedup_threshold": 0.93,
    "schedule": "0 2 * * *"
  }
}
```

Generate COMPLETE, WORKING code. No placeholders or pseudocode.
Keep total response under 8000 tokens."""

        self._add_message("user", synthesis_prompt)

        response = self._get_claude_response()

        # Parse JSON from response
        try:
            # Extract JSON from markdown code block
            if "```json" in response:
                json_start = response.index("```json") + 7
                # Use rindex to find the LAST ``` (not first, in case there are ``` in the JSON)
                json_end = response.rindex("```")
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response

            artifacts = json.loads(json_str)
            self.artifacts.update(artifacts)

        except Exception as e:
            logger.error(f"Error parsing artifacts: {e}")
            console.print(f"[red]Error parsing artifacts: {e}[/]")
            console.print("[yellow]Raw response (first 2000 chars):[/]")
            console.print(response[:2000])
            console.print("\n[yellow]... (truncated)[/]")

            # Save raw response to file for debugging
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
                f.write(response)
                console.print(f"\n[dim]Full response saved to: {f.name}[/]")

    def _display_results(self):
        """Display generated artifacts to user."""
        console.print()
        console.print(Panel.fit(
            "[bold green]✓ Discovery Complete![/]\n\n"
            f"Generated:\n"
            f"  • Plan document\n"
            f"  • {len(self.artifacts.get('scripts', []))} Python scripts\n"
            f"  • {len(self.artifacts.get('secrets', []))} required secrets\n"
            f"  • Configuration settings",
            title="🎉 Results",
            border_style="green"
        ))

        # Show secrets that need to be configured
        secrets = self.artifacts.get("secrets", [])
        if secrets:
            console.print("\n[bold yellow]⚠️  Required Secrets:[/]\n")
            for secret in secrets:
                console.print(f"  • {secret['key']}: {secret['description']}")
