#!/bin/bash

# ================================================================
# Test Runner - Run all database tests
# ================================================================
# Usage: ./tests/run-all-tests.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Database connection (use Supabase local)
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-54322}"
DB_NAME="${DB_NAME:-postgres}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"

export PGPASSWORD="$DB_PASSWORD"

echo ""
echo "================================================"
echo "Running Database Tests"
echo "================================================"
echo ""

# Check if database is accessible
echo "Checking database connection..."
if ! psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${RED}✗ Cannot connect to database${NC}"
    echo "  Make sure Supabase is running: ./bin/supabase start"
    exit 1
fi
echo -e "${GREEN}✓ Database connection OK${NC}"
echo ""

# Function to run a test file
run_test() {
    local test_file=$1
    local test_name=$(basename "$test_file" .sql)

    echo "Running: $test_name"
    echo "----------------------------------------"

    if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$test_file" 2>&1; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        return 1
    fi
}

# Track test results
TOTAL=0
PASSED=0
FAILED=0

# Run schema tests
echo "================================================"
echo "Schema Tests"
echo "================================================"
echo ""

for test_file in tests/schema/*.sql; do
    if [ -f "$test_file" ]; then
        TOTAL=$((TOTAL + 1))
        if run_test "$test_file"; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
        fi
        echo ""
    fi
done

# Run data tests (if any exist)
if [ -d "tests/data" ] && [ "$(ls -A tests/data/*.sql 2>/dev/null)" ]; then
    echo "================================================"
    echo "Data Tests"
    echo "================================================"
    echo ""

    for test_file in tests/data/*.sql; do
        if [ -f "$test_file" ]; then
            TOTAL=$((TOTAL + 1))
            if run_test "$test_file"; then
                PASSED=$((PASSED + 1))
            else
                FAILED=$((FAILED + 1))
            fi
            echo ""
        fi
    done
fi

# Run integration tests (if any exist)
if [ -d "tests/integration" ] && [ "$(ls -A tests/integration/*.sql 2>/dev/null)" ]; then
    echo "================================================"
    echo "Integration Tests"
    echo "================================================"
    echo ""

    for test_file in tests/integration/*.sql; do
        if [ -f "$test_file" ]; then
            TOTAL=$((TOTAL + 1))
            if run_test "$test_file"; then
                PASSED=$((PASSED + 1))
            else
                FAILED=$((FAILED + 1))
            fi
            echo ""
        fi
    done
fi

# Summary
echo "================================================"
echo "Test Summary"
echo "================================================"
echo ""
echo "Total:  $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Failed: $FAILED${NC}"
else
    echo -e "${GREEN}Failed: $FAILED${NC}"
fi
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed ✗${NC}"
    exit 1
fi
