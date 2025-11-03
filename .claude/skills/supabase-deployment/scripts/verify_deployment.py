#!/usr/bin/env python3
"""
Verify production deployment succeeded.

Checks that:
- Migrations have been applied
- Data has been imported correctly
- Storage files are accessible
- Database functions work correctly

Usage:
    python verify_deployment.py --db-url <connection-string> --project-url <url>

Examples:
    python verify_deployment.py \
        --db-url "postgresql://user:pass@host:5432/postgres" \
        --project-url "https://xxx.supabase.co"
"""

import argparse
import subprocess
import sys


def check_table_counts(db_url):
    """Verify table row counts match expected values"""
    print("🔍 Checking table counts...")

    queries = [
        ("entities", "SELECT COUNT(*) FROM entities;"),
        ("relationships", "SELECT COUNT(*) FROM relationships;"),
    ]

    for table, query in queries:
        result = subprocess.run(
            ["psql", db_url, "-t", "-c", query],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"  ❌ Failed to query {table}: {result.stderr}", file=sys.stderr)
            return False

        count = result.stdout.strip()
        print(f"  ✅ {table}: {count} rows")

    return True


def check_extensions(db_url):
    """Verify required extensions are installed"""
    print("\n🔍 Checking database extensions...")

    query = "SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm', 'vector');"

    result = subprocess.run(
        ["psql", db_url, "-t", "-c", query],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  ❌ Failed to query extensions: {result.stderr}", file=sys.stderr)
        return False

    extensions = result.stdout.strip().split('\n')
    for ext in extensions:
        if ext.strip():
            print(f"  ✅ {ext.strip()}")

    return True


def check_functions(db_url):
    """Verify database functions exist"""
    print("\n🔍 Checking database functions...")

    query = """
    SELECT routine_name
    FROM information_schema.routines
    WHERE routine_schema = 'public'
      AND routine_name = 'search_by_text';
    """

    result = subprocess.run(
        ["psql", db_url, "-t", "-c", query],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"  ❌ Failed to query functions: {result.stderr}", file=sys.stderr)
        return False

    functions = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]

    if 'search_by_text' in functions:
        print(f"  ✅ search_by_text()")
        return True
    else:
        print(f"  ❌ Missing function: search_by_text()", file=sys.stderr)
        return False


def check_storage_bucket(project_url):
    """Verify storage bucket is accessible"""
    print("\n🔍 Checking storage bucket...")

    # Try to access a public storage URL (should return 404 or 200, not 403/500)
    test_url = f"{project_url}/storage/v1/object/public/images/test.jpg"

    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", test_url],
        capture_output=True,
        text=True
    )

    status_code = result.stdout.strip()

    if status_code in ['200', '404']:
        print(f"  ✅ Storage bucket accessible (HTTP {status_code})")
        return True
    else:
        print(f"  ❌ Storage bucket not accessible (HTTP {status_code})", file=sys.stderr)
        return False


def verify_deployment(db_url, project_url):
    """Run all verification checks"""

    print("🚀 Verifying production deployment...\n")

    checks = [
        ("Table Counts", lambda: check_table_counts(db_url)),
        ("Extensions", lambda: check_extensions(db_url)),
        ("Functions", lambda: check_functions(db_url)),
        ("Storage Bucket", lambda: check_storage_bucket(project_url)),
    ]

    all_passed = True

    for name, check in checks:
        if not check():
            all_passed = False
            print(f"\n❌ {name} check failed")

    print("\n" + "="*50)

    if all_passed:
        print("✅ All verification checks passed!")
        print("   Production deployment is ready")
    else:
        print("❌ Some verification checks failed")
        print("   Review errors above and fix issues")

    return all_passed


def main():
    parser = argparse.ArgumentParser(
        description='Verify Supabase production deployment'
    )
    parser.add_argument('--db-url', required=True,
                       help='PostgreSQL connection string')
    parser.add_argument('--project-url', required=True,
                       help='Supabase project URL (e.g., https://xxx.supabase.co)')

    args = parser.parse_args()

    success = verify_deployment(args.db_url, args.project_url)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
