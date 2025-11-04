"""
Memory management with tiered importance strategy using Mem0.
"""

import json
from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pathlib import Path

from mem0 import Memory

from core.config import settings


MemoryCategory = Literal[
    "collection_structure",
    "strategy",
    "execution_state",
    "api_credentials",
    "workflow_pattern",
    "metadata_schema",
]


class TieredMemoryManager:
    """
    Manages curator agent memory with tiered importance strategy.

    Importance Levels:
    - 1.0 (Protected): Never pruned - collection structure, core rules
    - 0.7 (Strategic): Slowly pruned - import strategies, API patterns
    - 0.3 (Tactical): Aggressively pruned - execution state, temporary context
    """

    # Importance mappings by category
    CATEGORY_IMPORTANCE = {
        "collection_structure": 1.0,  # Protected
        "api_credentials": 1.0,  # Protected
        "metadata_schema": 1.0,  # Protected
        "strategy": 0.7,  # Strategic
        "workflow_pattern": 0.7,  # Strategic
        "execution_state": 0.3,  # Tactical
    }

    def __init__(self, curator_id: str):
        """
        Initialize memory manager for a specific curator.

        Args:
            curator_id: Unique identifier for the curator
        """
        self.curator_id = curator_id

        # Load Mem0 config based on LLM provider
        config_path = self._get_mem0_config_path()
        with open(config_path, "r") as f:
            mem0_config = json.load(f)

        # Initialize Mem0
        self.memory = Memory.from_config(mem0_config)

    def _get_mem0_config_path(self) -> Path:
        """Get Mem0 config path based on LLM provider."""
        # Try provider-specific config first
        provider_config = Path(f"config/mem0_{settings.llm_provider}.json")
        if provider_config.exists():
            return provider_config

        # Fall back to custom path or default
        if settings.mem0_config_path:
            return Path(settings.mem0_config_path)

        # Default to OpenAI config
        return Path("config/mem0_openai.json")

    def add(
        self,
        content: str,
        category: MemoryCategory,
        metadata: Optional[Dict[str, Any]] = None,
        custom_importance: Optional[float] = None,
    ) -> str:
        """
        Add a memory with tiered importance.

        Args:
            content: Memory content
            category: Memory category (determines default importance)
            metadata: Additional metadata
            custom_importance: Override default importance (0.0-1.0)

        Returns:
            Memory ID
        """
        importance = (
            custom_importance
            if custom_importance is not None
            else self.CATEGORY_IMPORTANCE[category]
        )

        # Build metadata
        full_metadata = {
            "curator_id": self.curator_id,
            "category": category,
            "importance": importance,
            "protected": importance >= 1.0,
            "timestamp": datetime.utcnow().isoformat(),
            **(metadata or {}),
        }

        # Add to Mem0
        result = self.memory.add(
            messages=content,
            user_id=self.curator_id,
            metadata=full_metadata,
        )

        # Mem0 returns {'results': [...]} where each result has an 'id'
        if result and "results" in result and result["results"]:
            return result["results"][0].get("id", "unknown")
        return "unknown"  # Fallback if no ID returned

    def search(
        self,
        query: str,
        category: Optional[MemoryCategory] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search memories by query with optional category filter.

        Args:
            query: Search query
            category: Optional category filter
            limit: Maximum results

        Returns:
            List of matching memories
        """
        # Build filter
        filters = {"curator_id": self.curator_id}
        if category:
            filters["category"] = category

        # Search
        response = self.memory.search(
            query=query,
            user_id=self.curator_id,
            limit=limit,
        )

        # Mem0 returns {'results': [...]}
        results = response.get('results', []) if isinstance(response, dict) else response

        # Filter by category if specified (Mem0 might not support all filters)
        if category:
            results = [r for r in results if r.get("metadata", {}).get("category") == category]

        return results

    def get_all(self, category: Optional[MemoryCategory] = None) -> List[Dict[str, Any]]:
        """
        Get all memories, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of memories
        """
        memories = self.memory.get_all(user_id=self.curator_id)

        if category:
            memories = [m for m in memories if m.get("metadata", {}).get("category") == category]

        return memories

    def update(self, memory_id: str, content: str) -> None:
        """
        Update memory content.

        Args:
            memory_id: Memory ID to update
            content: New content
        """
        self.memory.update(memory_id=memory_id, data=content)

    def delete(self, memory_id: str) -> None:
        """
        Delete a specific memory.

        Args:
            memory_id: Memory ID to delete
        """
        self.memory.delete(memory_id=memory_id)

    def add_collection_structure(
        self, collection_name: str, structure: Dict[str, Any]
    ) -> str:
        """
        Add protected collection structure memory.

        Args:
            collection_name: Collection name
            structure: Structure definition

        Returns:
            Memory ID
        """
        content = f"Collection '{collection_name}' structure: {json.dumps(structure, indent=2)}"
        return self.add(
            content=content,
            category="collection_structure",
            metadata={"collection_name": collection_name},
        )

    def add_strategy(
        self,
        strategy_name: str,
        description: str,
        success_rate: Optional[float] = None,
    ) -> str:
        """
        Add strategic memory about import strategies.

        Args:
            strategy_name: Strategy identifier
            description: Strategy description
            success_rate: Optional success rate (0.0-1.0)

        Returns:
            Memory ID
        """
        content = f"Import strategy '{strategy_name}': {description}"
        metadata = {"strategy_name": strategy_name}
        if success_rate is not None:
            metadata["success_rate"] = success_rate

        return self.add(content=content, category="strategy", metadata=metadata)

    def add_execution_state(self, state: Dict[str, Any]) -> str:
        """
        Add tactical execution state (will be pruned aggressively).

        Args:
            state: Current execution state

        Returns:
            Memory ID
        """
        content = f"Execution state: {json.dumps(state)}"
        return self.add(
            content=content, category="execution_state", metadata={"temporary": True}
        )

    def get_protected_memories(self) -> List[Dict[str, Any]]:
        """
        Get all protected memories (importance >= 1.0).

        Returns:
            List of protected memories
        """
        all_memories = self.get_all()
        return [m for m in all_memories if m.get("metadata", {}).get("protected", False)]
