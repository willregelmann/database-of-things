#!/bin/bash
#
# Export database data for production deployment
#
# This script exports only the data (not schema) from entities and relationships tables.
# The schema will be created via migrations in production.
#
# Usage:
#   ./export_data.sh [output_file]
#
# Examples:
#   ./export_data.sh                    # Outputs to production-data.sql
#   ./export_data.sh my-export.sql      # Custom output file

set -e

CONTAINER_NAME="supabase_db_database-of-things"
OUTPUT_FILE="${1:-production-data.sql}"

echo "📦 Exporting database data..."
echo "   Tables: entities, relationships"
echo "   Output: $OUTPUT_FILE"
echo ""

# Export data only (no schema, no ownership commands)
docker exec "$CONTAINER_NAME" pg_dump \
  -U postgres \
  -d postgres \
  --data-only \
  --no-owner \
  --no-privileges \
  --table=entities \
  --table=relationships \
  > "$OUTPUT_FILE"

# Check if export succeeded
if [ $? -eq 0 ]; then
    FILESIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    ENTITY_COUNT=$(docker exec "$CONTAINER_NAME" psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM entities;")
    REL_COUNT=$(docker exec "$CONTAINER_NAME" psql -U postgres -d postgres -t -c "SELECT COUNT(*) FROM relationships;")

    echo "✅ Export successful!"
    echo "   File size: $FILESIZE"
    echo "   Entities: $(echo $ENTITY_COUNT | xargs)"
    echo "   Relationships: $(echo $REL_COUNT | xargs)"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Link to production: ./bin/supabase link --project-ref YOUR_PROJECT_REF"
    echo "   2. Push migrations: ./scripts/safe-migrate push"
    echo "   3. Import data: psql -h YOUR_HOST -U postgres -d postgres -f $OUTPUT_FILE"
else
    echo "❌ Export failed!"
    exit 1
fi
