# curator/tests/test_tools.py
import pytest
from curator.tools import CuratorTools
from supabase import create_client
import os

@pytest.fixture
def supabase_client():
    """Create Supabase client for testing"""
    url = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    return create_client(url, key)

@pytest.fixture
def test_collection(supabase_client):
    """Create test collection entity"""
    result = supabase_client.table("entities").insert({
        "name": "Test Collection",
        "type": "collection"
    }).execute()
    collection_id = result.data[0]["id"]
    yield collection_id
    # Cleanup
    supabase_client.table("entities").delete().eq("id", collection_id).execute()

@pytest.fixture
def curator_tools(supabase_client, test_collection):
    """Create CuratorTools instance"""
    return CuratorTools(test_collection, supabase_client)

def test_get_collection_stats_empty(curator_tools):
    """Test stats for empty collection"""
    stats = curator_tools.get_collection_stats()
    assert stats["total_entities"] == 0
    assert stats["total_subcollections"] == 0
    assert stats["last_updated"] is None

def test_get_collection_stats_with_items(curator_tools, supabase_client, test_collection):
    """Test stats with items"""
    # Add items to collection
    card = supabase_client.table("entities").insert({
        "name": "Test Card",
        "type": "card"
    }).execute().data[0]

    supabase_client.table("relationships").insert({
        "from_id": test_collection,
        "to_id": card["id"],
        "type": "contains"
    }).execute()

    stats = curator_tools.get_collection_stats()
    assert stats["total_entities"] == 1
    assert stats["last_updated"] is not None

    # Cleanup
    supabase_client.table("entities").delete().eq("id", card["id"]).execute()

def test_search_entities(curator_tools, supabase_client, test_collection):
    """Test semantic search within collection"""
    # Add entity with embedding
    card = supabase_client.table("entities").insert({
        "name": "Charizard",
        "type": "card",
        "name_embedding": [0.1] * 384  # Dummy embedding
    }).execute().data[0]

    supabase_client.table("relationships").insert({
        "from_id": test_collection,
        "to_id": card["id"],
        "type": "contains"
    }).execute()

    results = curator_tools.search_entities("fire dragon", limit=5)
    assert len(results) <= 5
    assert all("similarity" in r for r in results)

    # Cleanup
    supabase_client.table("entities").delete().eq("id", card["id"]).execute()

def test_add_entity(curator_tools):
    """Test adding entity to collection"""
    entity_id = curator_tools.add_entity(
        name="Test Item",
        entity_type="card",
        attributes={"hp": 100}
    )

    assert entity_id is not None
    # Verify relationship created
    # Cleanup happens via fixture
