#!/usr/bin/env python3
"""Validate collection integrity and flag issues."""

import json
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = "data/catalog.db"
MAIN_COLLECTION = "Power Rangers Toys"

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def validate_parent_relationships(conn):
    """Check that all items have correct dual-parent structure."""
    cursor = conn.cursor()
    issues = []
    
    # Get all items with their parent count
    cursor.execute("""
        SELECT i.id, i.name, COUNT(ci.collection_id) as parent_count,
               GROUP_CONCAT(c.name, ' | ') as parents
        FROM items i
        LEFT JOIN collection_items ci ON i.id = ci.item_id
        LEFT JOIN collections c ON ci.collection_id = c.id
        GROUP BY i.id
        HAVING parent_count != 2
    """)
    
    for item_id, name, count, parents in cursor.fetchall():
        issues.append({
            'type': 'PARENT_COUNT',
            'severity': 'HIGH',
            'item_id': item_id,
            'item_name': name,
            'expected': 2,
            'actual': count,
            'parents': parents or 'None'
        })
    
    return issues

def validate_duplicates(conn):
    """Find duplicate product numbers."""
    cursor = conn.cursor()
    issues = []
    
    # Extract product numbers and find duplicates
    cursor.execute("SELECT id, name, metadata FROM items")
    product_map = defaultdict(list)
    
    for item_id, name, metadata_str in cursor.fetchall():
        # Extract product number from name
        parts = name.split()
        if parts and parts[0].isdigit():
            product_num = parts[0]
            product_map[product_num].append({
                'id': item_id,
                'name': name,
                'metadata': json.loads(metadata_str) if metadata_str else {}
            })
    
    # Report duplicates
    for product_num, items in product_map.items():
        if len(items) > 1:
            issues.append({
                'type': 'DUPLICATE_PRODUCT',
                'severity': 'MEDIUM',
                'product_number': product_num,
                'count': len(items),
                'items': [{'id': item['id'], 'name': item['name']} for item in items]
            })
    
    return issues

def validate_metadata(conn):
    """Check for missing critical metadata fields."""
    cursor = conn.cursor()
    issues = []
    
    cursor.execute("SELECT id, name, metadata FROM items")
    
    for item_id, name, metadata_str in cursor.fetchall():
        metadata = json.loads(metadata_str) if metadata_str else {}
        missing_fields = []
        
        # Check critical fields
        if not metadata.get('product_number'):
            missing_fields.append('product_number')
        if not metadata.get('series'):
            missing_fields.append('series')
        
        if missing_fields:
            issues.append({
                'type': 'MISSING_METADATA',
                'severity': 'MEDIUM',
                'item_id': item_id,
                'item_name': name,
                'missing_fields': missing_fields
            })
    
    return issues

def validate_images(conn):
    """Check for broken image paths."""
    cursor = conn.cursor()
    issues = []
    
    cursor.execute("SELECT id, name, metadata FROM items")
    
    for item_id, name, metadata_str in cursor.fetchall():
        metadata = json.loads(metadata_str) if metadata_str else {}
        local_image = metadata.get('image_local')
        
        if local_image and not Path(local_image).exists():
            issues.append({
                'type': 'BROKEN_IMAGE',
                'severity': 'LOW',
                'item_id': item_id,
                'item_name': name,
                'image_path': local_image
            })
    
    return issues

def generate_report(all_issues):
    """Generate validation report."""
    print("\n" + "="*60)
    print("POWER RANGERS TOYS - VALIDATION REPORT")
    print("="*60 + "\n")
    
    if not all_issues:
        print("✓ No issues found! Collection is valid.\n")
        return
    
    # Group by severity
    by_severity = defaultdict(list)
    for issue in all_issues:
        by_severity[issue['severity']].append(issue)
    
    for severity in ['HIGH', 'MEDIUM', 'LOW']:
        issues = by_severity[severity]
        if not issues:
            continue
        
        print(f"\n{severity} PRIORITY ({len(issues)} issues):")
        print("-" * 60)
        
        for issue in issues[:10]:  # Show first 10 per severity
            print(f"\n• {issue['type']}")
            for key, value in issue.items():
                if key not in ['type', 'severity']:
                    print(f"  {key}: {value}")
        
        if len(issues) > 10:
            print(f"\n  ... and {len(issues) - 10} more")
    
    print("\n" + "="*60 + "\n")

def main():
    conn = get_db_connection()
    all_issues = []
    
    print("Running validation checks...")
    
    print("  Checking parent relationships...")
    all_issues.extend(validate_parent_relationships(conn))
    
    print("  Checking for duplicates...")
    all_issues.extend(validate_duplicates(conn))
    
    print("  Checking metadata completeness...")
    all_issues.extend(validate_metadata(conn))
    
    print("  Checking image files...")
    all_issues.extend(validate_images(conn))
    
    conn.close()
    
    # Generate report
    generate_report(all_issues)
    
    # Save to JSON
    with open('validation_report.json', 'w') as f:
        json.dump(all_issues, f, indent=2)
    print("Full report saved to validation_report.json")

if __name__ == '__main__':
    main()
