"""Tests for fetched_data.json validation."""

import pytest

from curator.validator import validate
from curator.errors import ValidationError


class TestValidate:
    def test_valid_data_returns_parsed(self, sample_fetched_data):
        result = validate(sample_fetched_data)
        assert result["metadata"]["curator"] == "Test Curator"
        assert len(result["items"]) == 2

    def test_rejects_missing_format_version(self, sample_fetched_data):
        del sample_fetched_data["format_version"]
        with pytest.raises(ValidationError, match="format_version"):
            validate(sample_fetched_data)

    def test_rejects_wrong_format_version(self, sample_fetched_data):
        sample_fetched_data["format_version"] = "2.0"
        with pytest.raises(ValidationError, match="format_version"):
            validate(sample_fetched_data)

    def test_rejects_missing_items(self, sample_fetched_data):
        del sample_fetched_data["items"]
        with pytest.raises(ValidationError, match="items"):
            validate(sample_fetched_data)

    def test_rejects_empty_items(self, sample_fetched_data):
        sample_fetched_data["items"] = []
        with pytest.raises(ValidationError, match="empty"):
            validate(sample_fetched_data)

    def test_rejects_items_without_name(self, sample_fetched_data):
        sample_fetched_data["items"][0] = {"type": "card"}
        with pytest.raises(ValidationError, match="name"):
            validate(sample_fetched_data)

    def test_rejects_missing_metadata(self, sample_fetched_data):
        del sample_fetched_data["metadata"]
        with pytest.raises(ValidationError, match="metadata"):
            validate(sample_fetched_data)


class TestValidateFromFile:
    def test_loads_and_validates_file(self, tmp_path, sample_fetched_data):
        import json

        path = tmp_path / "fetched_data.json"
        path.write_text(json.dumps(sample_fetched_data))

        from curator.validator import validate_file

        result = validate_file(path)
        assert len(result["items"]) == 2

    def test_raises_on_missing_file(self, tmp_path):
        from curator.validator import validate_file

        with pytest.raises(ValidationError, match="not found"):
            validate_file(tmp_path / "nonexistent.json")

    def test_raises_on_invalid_json(self, tmp_path):
        from curator.validator import validate_file

        path = tmp_path / "fetched_data.json"
        path.write_text("{invalid json")
        with pytest.raises(ValidationError, match="parse"):
            validate_file(path)
