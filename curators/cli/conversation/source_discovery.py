"""
Source Discovery Agent - Discovers data sources from user instructions.

Uses LLM to understand intent and search for relevant data sources.
"""

from typing import List, Dict, Any
from core.llm import get_llm


class SourceDiscoveryAgent:
    """
    Discovers data sources autonomously using LLM.

    Analyzes user instructions to find relevant URLs, APIs, or data sources.
    """

    def __init__(self):
        """Initialize discovery agent."""
        self.llm = get_llm()

    async def discover(self, instructions: str) -> List[Dict[str, Any]]:
        """
        Discover data sources from instructions.

        Args:
            instructions: User instructions (e.g., "Import Elden Ring merchandise")

        Returns:
            List of discovered sources with metadata

        Note:
            Currently returns empty list, forcing manual URL entry.
            Full implementation would use LLM + web search to discover sources.
        """
        # TODO: Implement full source discovery with LLM
        # For now, return empty list to force manual URL entry
        return []
