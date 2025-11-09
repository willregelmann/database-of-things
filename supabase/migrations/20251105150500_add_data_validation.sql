-- ================================================================
-- Migration: Add data validation constraints
-- ================================================================
-- Adds validation rules to prevent common data quality issues
-- as we transition to multi-user production system

-- ================================================================
-- Entity Type Validation
-- ================================================================

-- Define allowed entity types (expand as needed)
CREATE TABLE IF NOT EXISTS entity_type_registry (
    type TEXT PRIMARY KEY,
    description TEXT,
    required_attributes JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with known types
INSERT INTO entity_type_registry (type, description, required_attributes) VALUES
    ('collection', 'Top-level collection grouping', '[]'),
    ('card', 'Trading card', '[]'),
    ('set', 'Card set or expansion', '[]'),
    ('figure', 'Action figure or collectible figure', '[]'),
    ('game', 'Video game', '[]'),
    ('franchise', 'Overall franchise/brand', '[]'),
    ('series', 'Series within a franchise', '[]'),
    ('toy', 'General toy or collectible', '[]')
ON CONFLICT (type) DO NOTHING;

-- Add check constraint for entity types
-- (We'll make this strict later after cleaning up existing data)
-- For now, just add the table and we'll reference it in application layer

-- ================================================================
-- Basic Data Quality Constraints
-- ================================================================

-- Name cannot be empty or just whitespace
ALTER TABLE entities ADD CONSTRAINT entities_name_not_empty
    CHECK (trim(name) != '');

-- Year must be reasonable if provided
ALTER TABLE entities ADD CONSTRAINT entities_year_reasonable
    CHECK (year IS NULL OR (year >= 1800 AND year <= 2100));

-- Country must be valid ISO 3166-1 alpha-2 if provided
ALTER TABLE entities ADD CONSTRAINT entities_country_iso
    CHECK (
        country IS NULL OR
        country ~ '^[A-Z]{2}$'
    );

-- Language must be valid ISO 639-1 if provided
ALTER TABLE entities ADD CONSTRAINT entities_language_iso
    CHECK (
        language IS NULL OR
        language ~ '^[a-z]{2}$'
    );

-- ================================================================
-- Image URL Validation
-- ================================================================

-- image_url must be a valid path or URL if provided
ALTER TABLE entities ADD CONSTRAINT entities_image_url_valid
    CHECK (
        image_url IS NULL OR
        image_url ~ '^(/storage/v1/object/public/images/|https?://)'
    );

-- thumbnail_url must be a valid path if provided
ALTER TABLE entities ADD CONSTRAINT entities_thumbnail_url_valid
    CHECK (
        thumbnail_url IS NULL OR
        thumbnail_url ~ '^/storage/v1/object/public/images/.+\.(webp|jpg|jpeg|png)$'
    );

-- If thumbnail exists, original image should exist
ALTER TABLE entities ADD CONSTRAINT entities_thumbnail_requires_image
    CHECK (
        thumbnail_url IS NULL OR image_url IS NOT NULL
    );

-- ================================================================
-- Relationship Validation
-- ================================================================

-- Relationship type must not be empty
ALTER TABLE relationships ADD CONSTRAINT relationships_type_not_empty
    CHECK (trim(type) != '');

-- Cannot create self-referential relationships (entity pointing to itself)
ALTER TABLE relationships ADD CONSTRAINT relationships_no_self_reference
    CHECK (from_id != to_id);

-- Order must be non-negative if provided
ALTER TABLE relationships ADD CONSTRAINT relationships_order_non_negative
    CHECK ("order" IS NULL OR "order" >= 0);

-- ================================================================
-- JSONB Structure Validation (Type-specific)
-- ================================================================

-- For cards: if hp exists in attributes, it must be a positive number
-- (Relaxed constraint - only validates IF the field exists)
CREATE OR REPLACE FUNCTION validate_card_attributes()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.type = 'card' AND NEW.attributes ? 'hp' THEN
        IF NOT (NEW.attributes->>'hp' ~ '^\d+$' AND (NEW.attributes->>'hp')::int > 0) THEN
            RAISE EXCEPTION 'Card hp must be a positive integer, got: %', NEW.attributes->>'hp';
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_card_attributes
    BEFORE INSERT OR UPDATE ON entities
    FOR EACH ROW
    WHEN (NEW.type = 'card')
    EXECUTE FUNCTION validate_card_attributes();

-- ================================================================
-- External IDs Validation
-- ================================================================

-- external_ids must be an object (not array, not scalar)
ALTER TABLE entities ADD CONSTRAINT entities_external_ids_is_object
    CHECK (
        external_ids IS NULL OR
        jsonb_typeof(external_ids) = 'object'
    );

-- attributes must be an object
ALTER TABLE entities ADD CONSTRAINT entities_attributes_is_object
    CHECK (
        attributes IS NULL OR
        jsonb_typeof(attributes) = 'object'
    );

-- ================================================================
-- Logging and Monitoring
-- ================================================================

-- Create a view to find entities that might have data quality issues
CREATE OR REPLACE VIEW entity_data_quality_issues AS
SELECT
    id,
    name,
    type,
    CASE
        WHEN name IS NULL OR trim(name) = '' THEN 'Empty name'
        WHEN type NOT IN (SELECT type FROM entity_type_registry) THEN 'Unknown entity type'
        WHEN image_url IS NOT NULL AND image_url !~ '^(/storage/v1/object/public/images/|https?://)' THEN 'Invalid image URL'
        WHEN year IS NOT NULL AND (year < 1800 OR year > 2100) THEN 'Invalid year'
        ELSE 'Other issue'
    END as issue_type,
    created_at
FROM entities
WHERE
    -- Has some data quality issue
    name IS NULL OR trim(name) = '' OR
    type NOT IN (SELECT type FROM entity_type_registry) OR
    (image_url IS NOT NULL AND image_url !~ '^(/storage/v1/object/public/images/|https?://)') OR
    (year IS NOT NULL AND (year < 1800 OR year > 2100));

COMMENT ON VIEW entity_data_quality_issues IS
    'Identifies entities with potential data quality issues for cleanup';

-- ================================================================
-- Grant permissions
-- ================================================================

GRANT SELECT ON entity_type_registry TO anon, authenticated;
GRANT SELECT ON entity_data_quality_issues TO authenticated;

-- Users can propose new entity types via application (not directly)
-- Application code will insert after validation
