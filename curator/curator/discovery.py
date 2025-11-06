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

Your goal: Through Socratic questioning, understand their collection and help them design an autonomous curator.

Key areas to explore:
1. **Collection Scope** - What items belong in this collection? How are they organized?
2. **Data Sources** - Where does data come from? APIs? Web scraping? Manual entry?
3. **Organization** - Should items be in subcollections? How should they be hierarchical?
4. **Metadata** - What attributes are important? What makes items unique?
5. **Update Frequency** - How often should the curator check for updates?
6. **Deduplication** - How should duplicates be detected? What's the threshold?

Ask thoughtful questions. Listen to their answers. Build understanding incrementally.

When you have sufficient understanding, generate:

1. **Plan Document** (Markdown)
   - Collection structure
   - Data sources and APIs
   - Update workflow
   - Deduplication strategy

2. **Scripts** (Python)
   - fetch_data.py - Fetch new items from source
   - update_existing.py - Update existing item metadata
   - deduplicate.py - Find and handle duplicates

3. **Secrets List**
   - Required API keys
   - Validation instructions

Use tools to inspect the current database state when helpful.

Important: Generate COMPLETE, WORKING scripts. Don't use pseudocode or placeholders.
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
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
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
2. Python scripts for data fetching and management
3. List of required secrets/API keys
4. Configuration settings (dedup threshold, schedule, etc)

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
    "schedule": "0 2 * * *",
    "...": "..."
  }
}
```

Generate COMPLETE, WORKING code. No placeholders or pseudocode."""

        self._add_message("user", synthesis_prompt)

        response = self._get_claude_response()

        # Parse JSON from response
        try:
            # Extract JSON from markdown code block
            if "```json" in response:
                json_start = response.index("```json") + 7
                json_end = response.index("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response

            artifacts = json.loads(json_str)
            self.artifacts.update(artifacts)

        except Exception as e:
            logger.error(f"Error parsing artifacts: {e}")
            console.print(f"[red]Error parsing artifacts: {e}[/]")
            console.print("[yellow]Raw response:[/]")
            console.print(response)

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
