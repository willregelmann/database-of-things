# curator/tests/test_storage.py
import pytest
from pathlib import Path
from curator.storage import CuratorStorage
import tempfile
import shutil

@pytest.fixture
def temp_curator_home():
    """Create temporary curator home directory"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

def test_curator_storage_init(temp_curator_home):
    """Test storage initialization"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    assert storage.curator_home.exists()
    assert (storage.curator_home / "curators").exists()
    assert (storage.curator_home / "runs").exists()

def test_create_curator_directory(temp_curator_home):
    """Test creating curator directory structure"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    curator_dir = storage.create_curator_directory("test-curator")

    assert curator_dir.exists()
    assert (curator_dir / "scripts").exists()
    assert (curator_dir / "memory").exists()
    assert (curator_dir / "config.json").exists()

def test_save_curator_plan(temp_curator_home):
    """Test saving curator plan"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    curator_dir = storage.create_curator_directory("test-curator")

    plan = "# Test Plan\n\nThis is a test plan."
    storage.save_plan("test-curator", plan)

    plan_file = curator_dir / "plan.md"
    assert plan_file.exists()
    assert plan_file.read_text() == plan

def test_save_scripts(temp_curator_home):
    """Test saving curator scripts"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    storage.create_curator_directory("test-curator")

    scripts = [
        {"filename": "fetch.py", "code": "print('hello')"},
        {"filename": "update.py", "code": "print('world')"}
    ]

    storage.save_scripts("test-curator", scripts)

    curator_dir = storage.curator_home / "curators" / "test-curator"
    assert (curator_dir / "scripts" / "fetch.py").exists()
    assert (curator_dir / "scripts" / "update.py").exists()

def test_save_secrets(temp_curator_home):
    """Test saving secrets"""
    storage = CuratorStorage(curator_home=temp_curator_home)
    storage.create_curator_directory("test-curator")

    secrets = {"API_KEY": "secret123", "TOKEN": "token456"}
    storage.save_secrets("test-curator", secrets)

    secrets_file = storage.curator_home / "curators" / "test-curator" / "secrets.env"
    assert secrets_file.exists()
    assert "API_KEY=secret123" in secrets_file.read_text()
