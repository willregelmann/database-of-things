"""Filesystem storage for curator configuration and artifacts."""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class CuratorStorage:
    """Manages curator filesystem storage.

    Directory structure:
        .curator/
        ├── curators/
        │   ├── pokemon-tcg/
        │   │   ├── config.json
        │   │   ├── plan.md
        │   │   ├── scripts/
        │   │   │   ├── fetch_sets.py
        │   │   │   └── fetch_cards.py
        │   │   ├── secrets.env
        │   │   └── memory/
        │   │       └── episodes.jsonl
        │   └── marvel-comics/...
        └── runs/
            └── pokemon-tcg/
                ├── 2025-11-06_120000/
                │   ├── log.txt
                │   └── operations.json
                └── 2025-11-06_140000/...
    """

    def __init__(self, curator_home: Optional[Path] = None):
        """Initialize storage.

        Args:
            curator_home: Root directory for curator storage
                         (defaults to .curator in current directory)
        """
        if curator_home is None:
            curator_home = Path.cwd() / ".curator"

        self.curator_home = Path(curator_home)
        self._ensure_structure()

    def _ensure_structure(self):
        """Ensure base directory structure exists."""
        self.curator_home.mkdir(exist_ok=True)
        (self.curator_home / "curators").mkdir(exist_ok=True)
        (self.curator_home / "runs").mkdir(exist_ok=True)

    def create_curator_directory(self, curator_name: str) -> Path:
        """Create directory structure for a new curator.

        Args:
            curator_name: Curator name (used as directory name)

        Returns:
            Path to curator directory
        """
        curator_dir = self.curator_home / "curators" / curator_name
        curator_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (curator_dir / "scripts").mkdir(exist_ok=True)
        (curator_dir / "memory").mkdir(exist_ok=True)

        # Create initial config
        config_file = curator_dir / "config.json"
        if not config_file.exists():
            config = {
                "name": curator_name,
                "created_at": datetime.now().isoformat(),
                "version": 1
            }
            config_file.write_text(json.dumps(config, indent=2))

        logger.info(f"Created curator directory: {curator_dir}")
        return curator_dir

    def get_curator_directory(self, curator_name: str) -> Path:
        """Get path to curator directory.

        Args:
            curator_name: Curator name

        Returns:
            Path to curator directory

        Raises:
            FileNotFoundError: If curator doesn't exist
        """
        curator_dir = self.curator_home / "curators" / curator_name
        if not curator_dir.exists():
            raise FileNotFoundError(f"Curator '{curator_name}' not found")
        return curator_dir

    def save_plan(self, curator_name: str, plan: str):
        """Save curator plan document.

        Args:
            curator_name: Curator name
            plan: Plan markdown content
        """
        curator_dir = self.get_curator_directory(curator_name)
        plan_file = curator_dir / "plan.md"
        plan_file.write_text(plan)
        logger.info(f"Saved plan for {curator_name}")

    def load_plan(self, curator_name: str) -> str:
        """Load curator plan document.

        Args:
            curator_name: Curator name

        Returns:
            Plan markdown content
        """
        curator_dir = self.get_curator_directory(curator_name)
        plan_file = curator_dir / "plan.md"
        return plan_file.read_text()

    def save_scripts(self, curator_name: str, scripts: List[Dict[str, str]]):
        """Save curator scripts.

        Args:
            curator_name: Curator name
            scripts: List of {"filename": "...", "code": "..."} dicts
        """
        curator_dir = self.get_curator_directory(curator_name)
        scripts_dir = curator_dir / "scripts"

        for script in scripts:
            filename = script["filename"]
            code = script["code"]
            script_file = scripts_dir / filename
            script_file.write_text(code)
            logger.info(f"Saved script: {filename}")

    def list_scripts(self, curator_name: str) -> List[str]:
        """List available scripts for curator.

        Args:
            curator_name: Curator name

        Returns:
            List of script filenames
        """
        curator_dir = self.get_curator_directory(curator_name)
        scripts_dir = curator_dir / "scripts"
        return [f.name for f in scripts_dir.glob("*.py")]

    def save_secrets(self, curator_name: str, secrets: Dict[str, str]):
        """Save curator secrets to .env file.

        Args:
            curator_name: Curator name
            secrets: Dict of {KEY: value} pairs
        """
        curator_dir = self.get_curator_directory(curator_name)
        secrets_file = curator_dir / "secrets.env"

        lines = [f"{key}={value}" for key, value in secrets.items()]
        secrets_file.write_text("\n".join(lines) + "\n")

        # Set restrictive permissions (owner read/write only)
        secrets_file.chmod(0o600)

        logger.info(f"Saved {len(secrets)} secrets for {curator_name}")

    def load_secrets(self, curator_name: str) -> Dict[str, str]:
        """Load curator secrets from .env file.

        Args:
            curator_name: Curator name

        Returns:
            Dict of {KEY: value} pairs
        """
        curator_dir = self.get_curator_directory(curator_name)
        secrets_file = curator_dir / "secrets.env"

        if not secrets_file.exists():
            return {}

        secrets = {}
        for line in secrets_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                secrets[key.strip()] = value.strip()

        return secrets

    def save_config(self, curator_name: str, config: Dict[str, Any]):
        """Save curator configuration.

        Args:
            curator_name: Curator name
            config: Configuration dict
        """
        curator_dir = self.get_curator_directory(curator_name)
        config_file = curator_dir / "config.json"
        config_file.write_text(json.dumps(config, indent=2))
        logger.info(f"Saved config for {curator_name}")

    def load_config(self, curator_name: str) -> Dict[str, Any]:
        """Load curator configuration.

        Args:
            curator_name: Curator name

        Returns:
            Configuration dict
        """
        curator_dir = self.get_curator_directory(curator_name)
        config_file = curator_dir / "config.json"
        return json.loads(config_file.read_text())

    def create_run_directory(self, curator_name: str) -> Path:
        """Create directory for a curator run.

        Args:
            curator_name: Curator name

        Returns:
            Path to run directory (timestamped)
        """
        runs_dir = self.curator_home / "runs" / curator_name
        runs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        run_dir = runs_dir / timestamp
        run_dir.mkdir(exist_ok=True)

        return run_dir

    def list_curators(self) -> List[str]:
        """List all curator names.

        Returns:
            List of curator names
        """
        curators_dir = self.curator_home / "curators"
        return [d.name for d in curators_dir.iterdir() if d.is_dir()]

    def curator_exists(self, curator_name: str) -> bool:
        """Check if curator exists.

        Args:
            curator_name: Curator name

        Returns:
            True if curator directory exists
        """
        curator_dir = self.curator_home / "curators" / curator_name
        return curator_dir.exists()
