"""Load curator configuration, secrets, and paths."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from curator.errors import ConfigError

# Default curators directory (relative to project root)
DEFAULT_CURATORS_DIR = Path(__file__).parent.parent / ".curator" / "curators"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=value pairs from a .env file, ignoring comments and blanks."""
    result = {}
    if not path.exists():
        return result
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            result[key] = value
    return result


@dataclass
class CuratorConfig:
    """Resolved curator configuration ready for pipeline use."""

    name: str
    curator_dir: Path
    data_source: str
    fetch_script: Path
    collection_id: str
    secrets: dict[str, str] = field(default_factory=dict)
    raw_config: dict = field(default_factory=dict)

    @property
    def fetched_data_path(self) -> Path:
        return self.curator_dir / "fetched_data.json"

    @property
    def status_path(self) -> Path:
        return self.curator_dir / "run_status.json"


def load_config(
    curator_name: str,
    env: str = "local",
    curators_dir: Path | None = None,
) -> CuratorConfig:
    """Load curator config, secrets, and resolve paths.

    Args:
        curator_name: Directory name under curators_dir.
        env: Environment name ("local" or "prod").
        curators_dir: Override path to curators parent directory.

    Returns:
        Fully resolved CuratorConfig.

    Raises:
        ConfigError: If curator directory, config.json, or collection ID missing.
    """
    base = curators_dir or DEFAULT_CURATORS_DIR
    curator_dir = base / curator_name

    if not curator_dir.is_dir():
        raise ConfigError(f"Curator '{curator_name}' not found at {curator_dir}")

    config_path = curator_dir / "config.json"
    if not config_path.exists():
        raise ConfigError(f"config.json not found in {curator_dir}")

    raw = json.loads(config_path.read_text())

    # Load secrets: shared first, then environment-specific
    shared_secrets = _parse_env_file(curator_dir / "secrets.env")
    env_secrets = _parse_env_file(curator_dir / f"secrets.{env}.env")
    all_secrets = {**shared_secrets, **env_secrets}

    collection_id = all_secrets.get("COLLECTION_ID", "")

    # Resolve fetch script path
    fetch_script_rel = raw.get("fetch", {}).get("script", "scripts/fetch_data.py")
    fetch_script = curator_dir / fetch_script_rel

    return CuratorConfig(
        name=raw.get("collection_name", curator_name),
        curator_dir=curator_dir,
        data_source=raw.get("data_source", ""),
        fetch_script=fetch_script,
        collection_id=collection_id,
        secrets=all_secrets,
        raw_config=raw,
    )
