#!/usr/bin/env python3
"""Import scraped toy lines into the database."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = "data/catalog.db"
INPUT_FILE = "scraped_toylines.json"
MAIN_COLLECTION = "Power Rangers Toys"
DRY_RUN = False  # Set to True to preview without committing

def get_db_connection():
    """Create database connection."""
    return sqlite3.connect(DB_PATH)

def ensure_collection_exists(conn, collection_name):
    """Create collection if it doesn't exist. Returns collection_id."""
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM collections WHERE name = ?", (collection_name,))
    result = cursor.fetchone()
    
    if result:
        return result[0]
    
    # Create new collection
    cursor.execute(
        "INSERT INTO collections (name, created_at) VALUES (?, ?)",
        (collection_name, datetime.now().isoformat())
    )
    conn.commit()
    return cursor.lastrowid

def get_existing_products(conn):
    """Get set of existing product numbers."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM items")
    
    existing = set()
    for (name,) in cursor.fetchall():
        # Extract product number from name
        parts = name.split()
        if parts and parts[0].isdigit():
            existing.add(parts[0])
    
    return existing

def create_item(conn, toy_data, main_collection_id, series_collection_id):
    """Create new item and link to collections."""
    cursor = conn.cursor()
    
    # Build item name: "2200 Mighty Morphin Power Rangers Red Ranger"
    item_name = f"{toy_data['product_number']} {toy_data['name']}"
    
    # Build metadata JSON
    metadata = {
        "product_number": toy_data['product_number'],
        "series": toy_data['series'],
        "year": toy_data.get('year'),
        "scale": toy_data.get('scale'),
        "description": toy_data.get('description'),
        "image_url": toy_data.get('image_url'),
        "image_local": toy_data.get('image_local'),
        "source": "rangerwiki",
        "source_url": toy_data.get('source_url'),
        "imported_at": datetime.now().isoformat()
    }
    
    # Create item
    cursor.execute(
        "INSERT INTO items (name, metadata, created_at) VALUES (?, ?, ?)",
        (item_name, json.dumps(metadata), datetime.now().isoformat())
    )
    item_id = cursor.lastrowid
    
    # Link to main collection
    cursor.execute(
        "INSERT INTO collection_items (collection_id, item_id, added_at) VALUES (?, ?, ?)",
        (main_collection_id, item_id, datetime.now().isoformat())
    )
    
    # Link to series collection
    cursor.execute(
        "INSERT INTO collection_items (collection_id, item_id, added_at) VALUES (?, ?, ?)",
        (series_collection_id, item_id, datetime.now().isoformat())
    )
    
    return item_id

def import_toys():
    """Main import function."""
    # Load scraped data
    with open(INPUT_FILE, 'r') as f:
        toys = json.load(f)
    
    print(f"Loaded {len(toys)} toy lines from {INPUT_FILE}")
    
    conn = get_db_connection()
    
    try:
        # Ensure main collection exists
        main_collection_id = ensure_collection_exists(conn, MAIN_COLLECTION)
        
        # Get existing products
        existing_products = get_existing_products(conn)
        print(f"Found {len(existing_products)} existing product numbers")
        
        # Import new toys
        imported = 0
        skipped = 0
        
        for toy in toys:
            product_num = toy['product_number']
            
            if product_num in existing_products:
                skipped += 1
                continue
            
            # Ensure series collection exists
            series_collection_id = ensure_collection_exists(conn, toy['series'])
            
            # Create item
            if not DRY_RUN:
                item_id = create_item(conn, toy, main_collection_id, series_collection_id)
                print(f"  Imported: {product_num} - {toy['name'][:50]}")
            else:
                print(f"  [DRY RUN] Would import: {product_num} - {toy['name'][:50]}")
            
            imported += 1
        
        if not DRY_RUN:
            conn.commit()
            print(f"\n✓ Successfully imported {imported} new toy lines")
        else:
            print(f"\n[DRY RUN] Would import {imported} new toy lines")
        
        print(f"✓ Skipped {skipped} existing items")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error during import: {e}")
        raise
    
    finally:
        conn.close()

if __name__ == '__main__':
    import_toys()
