# curator/tests/test_runner.py
import pytest
from curator.runner import CuratorRunner
from unittest.mock import Mock, patch

@pytest.fixture
def mock_storage():
    """Mock curator storage"""
    storage = Mock()
    storage.load_config.return_value = {
        "collection_id": "test-uuid",
        "dedup_threshold": 0.93
    }
    storage.load_plan.return_value = "# Test Plan"
    storage.list_scripts.return_value = ["fetch_data.py"]
    return storage

@pytest.fixture
def mock_supabase():
    """Mock Supabase client"""
    return Mock()

def test_runner_init(mock_storage, mock_supabase):
    """Test runner initialization"""
    runner = CuratorRunner(
        curator_name="test",
        storage=mock_storage,
        supabase_client=mock_supabase,
        anthropic_key="test-key"
    )
    assert runner.curator_name == "test"

def test_runner_executes_agent_loop(mock_storage, mock_supabase):
    """Test that runner executes agent decision loop"""
    runner = CuratorRunner(
        curator_name="test",
        storage=mock_storage,
        supabase_client=mock_supabase,
        anthropic_key="test-key"
    )

    with patch.object(runner, "_run_agent_loop") as mock_loop:
        mock_loop.return_value = {"status": "completed"}
        result = runner.run(dry_run=False)

        assert result["status"] == "completed"
        mock_loop.assert_called_once()
