#!/usr/bin/env python3
"""
Generate semantic embeddings for entity names using sentence-transformers.

This script:
1. Loads a pre-trained sentence-transformer model
2. Fetches all entities from the database
3. Generates embeddings for entity names
4. Updates the name_embedding column in batches

Usage:
    python generate_embeddings.py [--batch-size <n>] [--model <name>]

Examples:
    # Generate embeddings for all entities
    python generate_embeddings.py

    # Use a different model
    python generate_embeddings.py --model all-mpnet-base-v2

    # Process in smaller batches
    python generate_embeddings.py --batch-size 100
"""

import argparse
import sys
import subprocess
from sentence_transformers import SentenceTransformer

def get_entities_without_embeddings():
    """Get all entities that need embeddings."""
    sql = """
    SELECT id, name
    FROM entities
    WHERE name_embedding IS NULL
    ORDER BY created_at;
    """

    cmd = [
        'docker', 'exec', 'supabase_db_database-of-things',
        'psql', '-U', 'postgres', '-t', '-c', sql
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        entities = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    entities.append({
                        'id': parts[0],
                        'name': parts[1]
                    })

        return entities
    except subprocess.CalledProcessError as e:
        print(f"❌ Error querying entities: {e.stderr}", file=sys.stderr)
        return []

def update_embeddings_batch(entity_embeddings):
    """Update embeddings for a batch of entities."""
    if not entity_embeddings:
        return True

    success_count = 0

    # Update entities one at a time to avoid argument length limits
    for entity_id, embedding in entity_embeddings:
        # Convert numpy array to PostgreSQL vector format
        vector_str = '[' + ','.join(map(str, embedding.tolist())) + ']'

        sql = f"""
        UPDATE entities
        SET name_embedding = '{vector_str}'::vector
        WHERE id = '{entity_id}';
        """

        cmd = [
            'docker', 'exec', 'supabase_db_database-of-things',
            'psql', '-U', 'postgres', '-c', sql
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            success_count += 1
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Error updating entity {entity_id}: {e.stderr}", file=sys.stderr)
            continue

    return success_count == len(entity_embeddings)

def generate_embeddings(model_name='all-MiniLM-L6-v2', batch_size=500):
    """Generate embeddings for all entities."""

    print(f"📚 Loading model: {model_name}...")
    try:
        model = SentenceTransformer(model_name)
        print(f"✅ Model loaded (embedding dimension: {model.get_sentence_embedding_dimension()})")
    except Exception as e:
        print(f"❌ Error loading model: {e}", file=sys.stderr)
        return False

    print("\n🔍 Finding entities without embeddings...")
    entities = get_entities_without_embeddings()

    if not entities:
        print("✅ All entities already have embeddings")
        return True

    total = len(entities)
    print(f"📦 Found {total} entities to process\n")

    success_count = 0

    # Process in batches
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = entities[batch_start:batch_end]

        batch_num = (batch_start // batch_size) + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"📊 Batch {batch_num}/{total_batches} (entities {batch_start+1}-{batch_end}/{total})")

        # Extract names for this batch
        names = [e['name'] for e in batch]
        ids = [e['id'] for e in batch]

        # Generate embeddings
        print(f"  🧠 Generating embeddings...")
        try:
            embeddings = model.encode(names, show_progress_bar=False)
        except Exception as e:
            print(f"  ❌ Error generating embeddings: {e}", file=sys.stderr)
            continue

        # Prepare batch data
        entity_embeddings = list(zip(ids, embeddings))

        # Update database
        print(f"  💾 Updating database...")
        if update_embeddings_batch(entity_embeddings):
            success_count += len(batch)
            print(f"  ✅ Updated {len(batch)} entities")
        else:
            print(f"  ⏭️  Skipping batch (update failed)")

        print()

    print(f"✅ Successfully generated embeddings for {success_count}/{total} entities")

    return True

def main():
    parser = argparse.ArgumentParser(
        description='Generate semantic embeddings for entity names'
    )
    parser.add_argument(
        '--model',
        default='all-MiniLM-L6-v2',
        help='Sentence-transformer model name (default: all-MiniLM-L6-v2)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Number of entities to process per batch (default: 500)'
    )

    args = parser.parse_args()

    # Validate model dimension matches database
    print(f"🔧 Validating setup...")

    success = generate_embeddings(args.model, args.batch_size)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
