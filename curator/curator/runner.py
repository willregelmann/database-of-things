"""Curator execution engine."""

from typing import Dict, List, Any, Optional
from anthropic import Anthropic
from curator.storage import CuratorStorage
from curator.tools import CuratorTools
from datetime import datetime
from uuid import uuid4
import logging
import json

logger = logging.getLogger(__name__)


class CuratorRunner:
    """Executes curator runs with agent-driven decision making.

    The runner:
    1. Loads curator config and plan
    2. Creates tools for collection management
    3. Runs agent loop to decide actions
    4. Executes scripts as directed by agent
    5. Logs all operations for rollback/resume
    """

    def __init__(
        self,
        curator_name: str,
        storage: CuratorStorage,
        supabase_client,
        anthropic_key: str
    ):
        """Initialize runner.

        Args:
            curator_name: Name of curator to run
            storage: Curator storage instance
            supabase_client: Supabase client
            anthropic_key: Anthropic API key
        """
        self.curator_name = curator_name
        self.storage = storage
        self.db = supabase_client
        self.client = Anthropic(api_key=anthropic_key)

        # Load curator configuration
        self.config = storage.load_config(curator_name)
        self.collection_id = self.config["collection_id"]
        self.plan = storage.load_plan(curator_name)
        self.scripts = storage.list_scripts(curator_name)

        # Initialize tools
        self.tools = CuratorTools(self.collection_id, supabase_client)

        # Run tracking
        self.run_id = None
        self.operations = []

    def run(self, dry_run: bool = False) -> Dict[str, Any]:
        """Execute curator run.

        Args:
            dry_run: If True, show what would be done without executing

        Returns:
            Dict with run results:
            {
                "run_id": UUID,
                "status": "completed" | "failed",
                "operations_count": int,
                "summary": {...}
            }
        """
        # Create run record
        self.run_id = str(uuid4())
        run_start = datetime.now()

        logger.info(f"Starting curator run: {self.curator_name} (run_id: {self.run_id})")

        # Create run in database
        self.db.table("curator_runs").insert({
            "id": self.run_id,
            "curator_id": self._get_curator_db_id(),
            "trigger": "manual",
            "status": "running",
            "started_at": run_start.isoformat()
        }).execute()

        # Create run directory
        run_dir = self.storage.create_run_directory(self.curator_name)

        try:
            # Execute agent loop
            result = self._run_agent_loop(dry_run)

            # Mark run complete
            self.db.table("curator_runs").update({
                "status": "completed",
                "completed_at": datetime.now().isoformat(),
                "operations_count": len(self.operations),
                "summary": result.get("summary", {})
            }).eq("id", self.run_id).execute()

            # Update curator last_run_at
            self.db.table("curators").update({
                "last_run_at": datetime.now().isoformat()
            }).eq("id", self._get_curator_db_id()).execute()

            logger.info(f"Curator run completed: {self.curator_name}")

            return {
                "run_id": self.run_id,
                "status": "completed",
                "operations_count": len(self.operations),
                "summary": result.get("summary", {})
            }

        except Exception as e:
            logger.error(f"Curator run failed: {e}")

            # Mark run failed
            self.db.table("curator_runs").update({
                "status": "failed",
                "completed_at": datetime.now().isoformat(),
                "error": str(e)
            }).eq("id", self.run_id).execute()

            return {
                "run_id": self.run_id,
                "status": "failed",
                "error": str(e)
            }

    def _run_agent_loop(self, dry_run: bool) -> Dict[str, Any]:
        """Run agent decision loop.

        Args:
            dry_run: If True, don't execute actions

        Returns:
            Dict with agent decisions and results
        """
        # Get current collection state
        stats = self.tools.get_collection_stats()

        # Build agent prompt
        system_prompt = self._build_agent_system_prompt()
        user_prompt = self._build_agent_user_prompt(stats)

        # Call Claude with tools
        response = self.client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            tools=self.tools.to_anthropic_tools()
        )

        # Process tool calls
        result = self._process_agent_response(response, dry_run)

        return result

    def _build_agent_system_prompt(self) -> str:
        """Build system prompt for agent."""
        return f"""You are the {self.curator_name} curator agent.

Your plan:
{self.plan}

Your role: Assess the current state of your collection and decide what actions to take.

Available tools:
- Collection management (get_collection_stats, search_entities, etc.)
- Entity operations (add_entity, etc.)

Available scripts in scripts/:
{chr(10).join(f'  - {s}' for s in self.scripts)}

Process:
1. Use tools to assess current collection state
2. Decide what needs to be done (based on your plan)
3. Execute appropriate actions
4. Summarize what you did

Be autonomous but cautious. Don't make changes unless there's clear need."""

    def _build_agent_user_prompt(self, stats: Dict[str, Any]) -> str:
        """Build user prompt with context."""
        return f"""Time to run! Here's the current state:

**Collection Statistics:**
- Total entities: {stats['total_entities']}
- Subcollections: {stats['total_subcollections']}
- Entities by type: {stats['entities_by_type']}
- Last updated: {stats['last_updated']}
- Embedding coverage: {stats['has_embeddings']}/{stats['total_entities']}
- Thumbnail coverage: {stats['has_thumbnails']}/{stats['total_entities']}

**Your Task:**
1. Assess what needs to be done (check for new items, updates, etc.)
2. Use tools to investigate further if needed
3. Take appropriate actions
4. Summarize your work

What would you like to do?"""

    def _process_agent_response(
        self,
        response,
        dry_run: bool
    ) -> Dict[str, Any]:
        """Process agent response and execute tool calls.

        Args:
            response: Anthropic API response
            dry_run: If True, don't execute actions

        Returns:
            Dict with execution results
        """
        results = {
            "tool_calls": [],
            "summary": {}
        }

        # Extract tool calls
        for block in response.content:
            if hasattr(block, "type") and block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                logger.info(f"Agent called: {tool_name}({tool_input})")

                if dry_run:
                    results["tool_calls"].append({
                        "tool": tool_name,
                        "input": tool_input,
                        "executed": False
                    })
                else:
                    # Execute tool
                    tool_result = self._execute_tool(tool_name, tool_input)
                    results["tool_calls"].append({
                        "tool": tool_name,
                        "input": tool_input,
                        "result": tool_result,
                        "executed": True
                    })

        return results

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute a tool call.

        Args:
            tool_name: Name of tool to execute
            tool_input: Tool input parameters

        Returns:
            Tool execution result
        """
        # Map tool names to methods
        tool_methods = {
            "get_collection_stats": self.tools.get_collection_stats,
            "get_subcollections": self.tools.get_subcollections,
            "search_entities": self.tools.search_entities,
            "get_recent_additions": self.tools.get_recent_additions,
            "find_duplicates": self.tools.find_duplicates,
            "add_entity": self.tools.add_entity
        }

        tool_method = tool_methods.get(tool_name)
        if not tool_method:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Execute tool
        result = tool_method(**tool_input)

        # Log operation
        self._log_operation(tool_name, tool_input, result)

        return result

    def _log_operation(
        self,
        operation_type: str,
        data: Dict[str, Any],
        result: Any
    ):
        """Log operation for rollback/resume.

        Args:
            operation_type: Type of operation
            data: Operation input data
            result: Operation result
        """
        operation = {
            "id": str(uuid4()),
            "curator_id": self._get_curator_db_id(),
            "run_id": self.run_id,
            "operation_type": operation_type,
            "status": "completed",
            "data": {
                "input": data,
                "result": str(result)[:1000]  # Truncate for storage
            },
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }

        self.operations.append(operation)

        # Save to database
        self.db.table("curator_operations").insert(operation).execute()

    def _get_curator_db_id(self) -> str:
        """Get curator ID from database.

        Returns:
            Curator UUID
        """
        result = self.db.table("curators").select("id").eq(
            "name", self.curator_name
        ).single().execute()
        return result.data["id"]
