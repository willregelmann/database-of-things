-- Drop the unused attributes column from relationships table
-- All relationships currently have empty JSONB objects ({}) in this column
-- We use the dedicated 'order' column instead for relationship ordering

-- Drop the index first if it exists
DROP INDEX IF EXISTS idx_relationships_attributes;

-- Drop the attributes column
ALTER TABLE relationships DROP COLUMN IF EXISTS attributes;
