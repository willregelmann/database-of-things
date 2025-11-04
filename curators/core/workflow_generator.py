"""
Workflow Generator - Phase C: Dynamic Artifact Creation

Generates executable Python code and LangGraph workflows based on discovery findings.
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from rich.console import Console

from core.memory import TieredMemoryManager

console = Console()


class WorkflowGenerator:
    """
    Generates executable artifacts (Python scripts, workflows) based on discovery.

    Instead of hand-coding scrapers, this generator:
    - Takes discovery report as input
    - Uses LLM to generate working Python code
    - Creates complete, runnable artifacts
    - Stores them for execution
    """

    def __init__(self, llm, memory: TieredMemoryManager, artifacts_dir: Path):
        """
        Initialize workflow generator.

        Args:
            llm: Language model for code generation
            memory: Memory manager for storing artifacts
            artifacts_dir: Directory to save generated files
        """
        self.llm = llm
        self.memory = memory
        self.artifacts_dir = artifacts_dir

    async def generate(
        self,
        discovery_report: Dict[str, Any],
        goal: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """
        Generate workflow artifacts based on discovery.

        Args:
            discovery_report: Output from DiscoveryAgent
            goal: User's goal
            collection_id: Target collection UUID

        Returns:
            Metadata about generated artifacts
        """
        console.print("[cyan]Generating workflow artifacts...[/cyan]\n")

        analysis = discovery_report.get("analysis", {})
        extraction_strategy = analysis.get("extraction_strategy", "html_scraping")

        if extraction_strategy == "html_scraping":
            return await self._generate_scraper(discovery_report, goal, collection_id)
        elif extraction_strategy == "json_parsing":
            return await self._generate_json_parser(discovery_report, goal, collection_id)
        elif extraction_strategy == "api_calls":
            return await self._generate_api_client(discovery_report, goal, collection_id)
        else:
            # Fallback to generic scraper
            return await self._generate_scraper(discovery_report, goal, collection_id)

    async def _generate_scraper(
        self,
        discovery_report: Dict[str, Any],
        goal: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """Generate a web scraper based on discovery report."""

        console.print("[dim]Generating HTML scraper...[/dim]")

        # Build prompt for code generation
        prompt = self._build_scraper_prompt(discovery_report, goal, collection_id)

        # Invoke LLM to generate code
        console.print("[dim]Asking LLM to generate Python code...[/dim]")
        response = await self.llm.ainvoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Extract code from response
        code = self._extract_code_from_response(response_text)

        # Save to file
        scraper_file = self.artifacts_dir / "scraper.py"
        with open(scraper_file, "w") as f:
            f.write(code)

        console.print(f"[green]✅ Generated scraper: {scraper_file}[/green]")

        # Store in memory
        artifact_text = f"Generated scraper for {discovery_report.get('url')}: {scraper_file}"
        self.memory.add(
            content=artifact_text,
            category="workflow_pattern",  # Strategic importance 0.7
            metadata={
                "artifact_type": "scraper",
                "file_path": str(scraper_file),
                "goal": goal,
                "source_url": discovery_report.get("url")
            }
        )

        return {
            "artifact_type": "scraper",
            "files": {
                "scraper": str(scraper_file)
            },
            "generated_at": datetime.now().isoformat()
        }

    def _build_scraper_prompt(
        self,
        discovery_report: Dict[str, Any],
        goal: str,
        collection_id: str
    ) -> str:
        """Build LLM prompt for scraper generation."""

        analysis = discovery_report.get("analysis", {})
        url = discovery_report.get("url")

        return f"""Generate a complete, working Python web scraper based on this analysis.

GOAL: {goal}
SOURCE URL: {url}
TARGET COLLECTION ID: {collection_id}

DISCOVERY ANALYSIS:
{json.dumps(analysis, indent=2)}

Generate a Python script that:
1. Scrapes products from the source URL
2. Extracts all available data (name, price, image, etc.)
3. Categorizes products intelligently
4. Imports into the database using SupabaseClient
5. Handles errors gracefully
6. Includes progress logging with rich.console

REQUIREMENTS:
- Use asyncio for async operations
- Use httpx.AsyncClient for HTTP requests
- Use BeautifulSoup for HTML parsing
- Use the provided CSS selectors from the analysis
- Import SupabaseClient from utilities.supabase_client
- Use rich.console.Console for logging
- Handle pagination if available
- Include proper error handling
- Add a main() function that runs the scraper
- Make it executable with: python3 scraper.py

IMPORTANT CODE STRUCTURE:
```python
import asyncio
import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from utilities.supabase_client import SupabaseClient

console = Console()

async def fetch_page(url: str) -> str:
    # Implementation

def parse_products(html: str) -> list:
    # Use the selectors from analysis
    # Return list of product dicts

async def import_product(db: SupabaseClient, product: dict, category_id: str) -> str:
    # Create entity and relationships
    # Return product ID

async def main():
    # Main orchestration
    # 1. Initialize SupabaseClient
    # 2. Get category collection IDs (query database)
    # 3. Scrape all pages
    # 4. Import products
    # 5. Print stats

if __name__ == "__main__":
    asyncio.run(main())
```

Generate ONLY the complete Python code, no explanations.
Start with imports and end with the if __name__ block.
"""

    async def _generate_json_parser(
        self,
        discovery_report: Dict[str, Any],
        goal: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """Generate a JSON parser for API responses."""
        # Simplified for now - similar structure to _generate_scraper
        console.print("[yellow]JSON parser generation not fully implemented yet[/yellow]")
        return await self._generate_scraper(discovery_report, goal, collection_id)

    async def _generate_api_client(
        self,
        discovery_report: Dict[str, Any],
        goal: str,
        collection_id: str
    ) -> Dict[str, Any]:
        """Generate an API client."""
        # Simplified for now - similar structure to _generate_scraper
        console.print("[yellow]API client generation not fully implemented yet[/yellow]")
        return await self._generate_scraper(discovery_report, goal, collection_id)

    def _extract_code_from_response(self, response_text: str) -> str:
        """Extract Python code from LLM response."""

        # If response is wrapped in markdown code blocks
        if "```python" in response_text:
            parts = response_text.split("```python")
            if len(parts) > 1:
                code = parts[1].split("```")[0].strip()
                return code

        elif "```" in response_text:
            parts = response_text.split("```")
            if len(parts) >= 3:
                # Get the middle part (between first and second ```)
                code = parts[1].strip()
                # Remove language identifier if present
                if code.startswith("python\n"):
                    code = code[7:]
                return code

        # Otherwise, return as-is and hope it's valid Python
        return response_text.strip()
