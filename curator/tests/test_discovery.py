# curator/tests/test_discovery.py
import pytest
from curator.discovery import DiscoverySession
from anthropic import Anthropic
from unittest.mock import Mock, patch

@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client"""
    with patch("curator.discovery.Anthropic") as mock:
        yield mock

def test_discovery_session_init():
    """Test discovery session initialization"""
    session = DiscoverySession(
        curator_name="Test Curator",
        collection_id="test-uuid",
        anthropic_key="test-key"
    )
    assert session.curator_name == "Test Curator"
    assert session.collection_id == "test-uuid"
    assert len(session.conversation_history) == 0

def test_discovery_generates_plan(mock_anthropic):
    """Test that discovery session generates a plan"""
    session = DiscoverySession(
        curator_name="Test Curator",
        collection_id="test-uuid",
        anthropic_key="test-key"
    )

    # Mock user responses
    with patch("builtins.input", side_effect=["Pokemon cards", "pokemontcg.io API", "done"]):
        result = session.run()

    assert result["plan"] is not None
    assert result["scripts"] is not None
    assert result["secrets"] is not None
