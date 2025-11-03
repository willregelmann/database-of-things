#!/usr/bin/env python3
"""
Semantic search for entities using vector embeddings.

This script:
1. Loads the same sentence-transformer model used to generate embeddings
2. Encodes the search query into a vector
3. Queries the database for similar entities using cosine similarity
4. Returns ranked results with similarity scores

Usage:
    python semantic_search.py "<query>" [--limit <n>] [--type <type>]

Examples:
    # Search for entities similar to "fire dragon pokemon"
    python semantic_search.py "fire dragon pokemon"

    # Limit results to top 10
    python semantic_search.py "electric mouse" --limit 10

    # Search only within cards
    python semantic_search.py "pikachu" --type trading_card

    # Search within collections
    python semantic_search.py "base set" --type collection
"""

import argparse
import sys
import subprocess
from sentence_transformers import SentenceTransformer

def semantic_search(query, limit=20, entity_type=None, model_name='all-MiniLM-L6-v2'):
    """
    Search for entities semantically similar to the query.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        entity_type: Optional entity type filter
        model_name: Sentence-transformer model name

    Returns:
        List of matching entities with similarity scores
    """

    print(f"📚 Loading model: {model_name}...")
    try:
        model = SentenceTransformer(model_name)
    except Exception as e:
        print(f"❌ Error loading model: {e}", file=sys.stderr)
        return []

    print(f"🧠 Encoding query: \"{query}\"...")
    try:
        query_embedding = model.encode(query, show_progress_bar=False)
    except Exception as e:
        print(f"❌ Error encoding query: {e}", file=sys.stderr)
        return []

    # Convert numpy array to PostgreSQL vector format
    vector_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'

    # Build SQL query with vector similarity search
    type_filter = f"AND type = '{entity_type}'" if entity_type else ""

    sql = f"""
    SELECT
        id,
        name,
        type,
        year,
        country,
        language,
        image_url,
        1 - (name_embedding <=> '{vector_str}'::vector) as similarity
    FROM entities
    WHERE name_embedding IS NOT NULL
    {type_filter}
    ORDER BY name_embedding <=> '{vector_str}'::vector
    LIMIT {limit};
    """

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-t', '-c', sql
    ]

    print(f"🔍 Searching database...\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        entities = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 8:
                    entities.append({
                        'id': parts[0],
                        'name': parts[1],
                        'type': parts[2],
                        'year': parts[3] if parts[3] else None,
                        'country': parts[4] if parts[4] else None,
                        'language': parts[5] if parts[5] else None,
                        'image_url': parts[6] if parts[6] else None,
                        'similarity': float(parts[7]) if parts[7] else 0.0
                    })

        return entities
    except subprocess.CalledProcessError as e:
        print(f"❌ Error querying database: {e.stderr}", file=sys.stderr)
        return []

def format_results(entities):
    """Format search results for display."""
    if not entities:
        print("No results found.")
        return

    print(f"Found {len(entities)} results:\n")

    for i, entity in enumerate(entities, 1):
        # Calculate percentage similarity
        similarity_pct = entity['similarity'] * 100

        # Color code by similarity
        if similarity_pct >= 80:
            indicator = "🟢"
        elif similarity_pct >= 60:
            indicator = "🟡"
        else:
            indicator = "🔴"

        # Format metadata
        metadata_parts = []
        if entity['year']:
            metadata_parts.append(str(entity['year']))
        if entity['language']:
            metadata_parts.append(entity['language'].upper())
        if entity['country']:
            metadata_parts.append(entity['country'].upper())

        metadata = f" ({', '.join(metadata_parts)})" if metadata_parts else ""

        print(f"{indicator} {i}. {entity['name']}")
        print(f"   Type: {entity['type']}{metadata}")
        print(f"   Similarity: {similarity_pct:.1f}%")
        if entity['image_url']:
            print(f"   Image: {entity['image_url'][:60]}{'...' if len(entity['image_url']) > 60 else ''}")
        print()

def main():
    parser = argparse.ArgumentParser(
        description='Semantic search for entities using vector embeddings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python semantic_search.py "fire dragon pokemon"
  python semantic_search.py "electric mouse" --limit 10
  python semantic_search.py "pikachu" --type trading_card
  python semantic_search.py "base set" --type collection
        """
    )
    parser.add_argument(
        'query',
        help='Search query (natural language)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Maximum number of results (default: 20)'
    )
    parser.add_argument(
        '--type',
        dest='entity_type',
        help='Filter by entity type (e.g., collection, trading_card)'
    )
    parser.add_argument(
        '--model',
        default='all-MiniLM-L6-v2',
        help='Sentence-transformer model name (default: all-MiniLM-L6-v2)'
    )

    args = parser.parse_args()

    # Validate limit
    if args.limit < 1 or args.limit > 1000:
        print("❌ Error: --limit must be between 1 and 1000", file=sys.stderr)
        sys.exit(1)

    # Perform search
    entities = semantic_search(
        args.query,
        limit=args.limit,
        entity_type=args.entity_type,
        model_name=args.model
    )

    # Display results
    format_results(entities)

if __name__ == '__main__':
    main()
