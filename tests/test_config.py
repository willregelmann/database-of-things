"""Tests for curator config loading."""

from pathlib import Path

import pytest

from curator.config import CuratorConfig, load_config
from curator.errors import ConfigError


@pytest.fixture
def fake_curator_dir(fixtures_dir):
    return fixtures_dir / "fake_curator"


class TestLoadConfig:
    def test_loads_config_json(self, fake_curator_dir):
        config = load_config("fake_curator", curators_dir=fake_curator_dir.parent)
        assert config.name == "Fake Curator"
        assert config.data_source == "https://example.com"

    def test_loads_local_secrets(self, fake_curator_dir):
        config = load_config("fake_curator", env="local", curators_dir=fake_curator_dir.parent)
        assert config.collection_id == "00000000-1111-2222-3333-444444444444"

    def test_loads_prod_secrets(self, fake_curator_dir):
        config = load_config("fake_curator", env="prod", curators_dir=fake_curator_dir.parent)
        assert config.collection_id == "55555555-6666-7777-8888-999999999999"

    def test_loads_shared_secrets(self, fake_curator_dir):
        config = load_config("fake_curator", curators_dir=fake_curator_dir.parent)
        assert config.secrets["API_KEY"] == "test-key-123"

    def test_resolves_fetch_script_path(self, fake_curator_dir):
        config = load_config("fake_curator", curators_dir=fake_curator_dir.parent)
        assert config.fetch_script.exists()
        assert config.fetch_script.name == "fetch_data.py"

    def test_raises_on_missing_curator(self, fixtures_dir):
        with pytest.raises(ConfigError, match="not found"):
            load_config("nonexistent", curators_dir=fixtures_dir)

    def test_raises_on_missing_config_json(self, tmp_path):
        (tmp_path / "empty_curator").mkdir()
        with pytest.raises(ConfigError, match="config.json"):
            load_config("empty_curator", curators_dir=tmp_path)

    def test_curator_dir_path(self, fake_curator_dir):
        config = load_config("fake_curator", curators_dir=fake_curator_dir.parent)
        assert config.curator_dir == fake_curator_dir
