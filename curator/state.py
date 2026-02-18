"""Track curator run state via run_status.json."""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


class Phase(enum.Enum):
    """Pipeline phases in execution order."""

    NONE = "none"
    FETCHED = "fetched"
    VALIDATED = "validated"
    IMPORTED = "imported"

    def __lt__(self, other):
        if not isinstance(other, Phase):
            return NotImplemented
        order = list(Phase)
        return order.index(self) < order.index(other)

    def __le__(self, other):
        return self == other or self < other


@dataclass
class RunStatus:
    """Current state of a curator run."""

    phase: Phase = Phase.NONE
    result: str | None = None
    last_run: str | None = None
    summary: dict = field(default_factory=dict)


def load_status(path: Path) -> RunStatus:
    """Load run status from file, returning empty status if missing.

    Args:
        path: Path to run_status.json.

    Returns:
        RunStatus with current phase and metadata.
    """
    if not path.exists():
        return RunStatus()

    try:
        data = json.loads(path.read_text())
        return RunStatus(
            phase=Phase(data.get("phase", "none")),
            result=data.get("result"),
            last_run=data.get("last_run"),
            summary=data.get("summary", {}),
        )
    except (json.JSONDecodeError, ValueError):
        return RunStatus()


def write_status(
    path: Path,
    phase: Phase,
    result: str | None = None,
    summary: dict | None = None,
):
    """Write run status to file.

    Args:
        path: Path to run_status.json.
        phase: Current pipeline phase.
        result: "success" or "error".
        summary: Optional import summary dict.
    """
    data = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "phase": phase.value,
        "result": result,
        "summary": summary or {},
    }
    path.write_text(json.dumps(data, indent=2) + "\n")
