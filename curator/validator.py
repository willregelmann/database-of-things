"""Validate fetched_data.json against v1.0 schema."""

from __future__ import annotations

import json
from pathlib import Path

from curator.errors import ValidationError


def validate(data: dict) -> dict:
    """Validate a parsed fetched_data.json dict.

    Args:
        data: Parsed JSON data.

    Returns:
        The same data dict if valid.

    Raises:
        ValidationError: If data fails schema checks.
    """
    errors = []

    if data.get("format_version") != "1.0":
        errors.append("format_version must be '1.0'")

    if "metadata" not in data:
        errors.append("metadata section is required")

    if "items" not in data:
        errors.append("items array is required")
    elif not isinstance(data["items"], list):
        errors.append("items must be an array")
    elif len(data["items"]) == 0:
        errors.append("items array is empty")
    else:
        for i, item in enumerate(data["items"]):
            if not item.get("name"):
                errors.append(f"item[{i}] missing required field 'name'")

    if errors:
        raise ValidationError(
            f"Validation failed with {len(errors)} error(s): {errors[0]}",
            errors=errors,
        )

    return data


def validate_file(path: Path) -> dict:
    """Load and validate a fetched_data.json file.

    Args:
        path: Path to the JSON file.

    Returns:
        Validated data dict.

    Raises:
        ValidationError: If file missing, unparseable, or fails schema checks.
    """
    if not path.exists():
        raise ValidationError(f"File not found: {path}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValidationError(f"Failed to parse JSON: {e}") from e

    return validate(data)
