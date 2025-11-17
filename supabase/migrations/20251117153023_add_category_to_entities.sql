-- ============================================
-- ADD CATEGORY TO ENTITIES
-- Single category field for primary classification
-- ============================================

-- 1. Create category_type enum
CREATE TYPE category_type AS ENUM (
  'trading_card_games',
  'figures',
  'comics',
  'video_games',
  'buildables'
);

-- 2. Add category column to entities (nullable)
ALTER TABLE entities ADD COLUMN category category_type;

-- 3. Existing data starts with NULL category
-- Categories will be populated during future imports and updates
-- (Old type data was already converted to entity_type enum in migration 20251117140439)

-- 4. Create partial index for filtering (only indexes non-NULL values)
CREATE INDEX idx_entities_category ON entities(category)
WHERE category IS NOT NULL;

-- 5. Add helper function to get all available categories
CREATE OR REPLACE FUNCTION get_categories() RETURNS TEXT[] AS $$
  SELECT array_agg(enumlabel::text ORDER BY enumsortorder)
  FROM pg_enum WHERE enumtypid = 'category_type'::regtype;
$$ LANGUAGE sql IMMUTABLE;
