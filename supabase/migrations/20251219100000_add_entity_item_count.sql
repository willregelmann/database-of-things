-- ============================================
-- ADD ITEM_COUNT TO ENTITIES
-- Denormalized count of child relationships for fast lookups
-- ============================================

-- Add item_count column (nullable initially for backfill)
ALTER TABLE entities ADD COLUMN item_count INT DEFAULT 0;

-- Create index for queries filtering by item_count
CREATE INDEX idx_entities_item_count ON entities(item_count) WHERE item_count > 0;

-- ============================================
-- TRIGGER FUNCTION
-- Maintains item_count when relationships change
-- ============================================

CREATE OR REPLACE FUNCTION update_entity_item_count()
RETURNS TRIGGER AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    -- Increment count on the parent entity
    UPDATE entities
    SET item_count = item_count + 1
    WHERE id = NEW.from_id;
    RETURN NEW;

  ELSIF TG_OP = 'DELETE' THEN
    -- Decrement count on the parent entity
    UPDATE entities
    SET item_count = GREATEST(item_count - 1, 0)
    WHERE id = OLD.from_id;
    RETURN OLD;

  ELSIF TG_OP = 'UPDATE' THEN
    -- Handle from_id change (rare but possible)
    IF OLD.from_id != NEW.from_id THEN
      UPDATE entities
      SET item_count = GREATEST(item_count - 1, 0)
      WHERE id = OLD.from_id;

      UPDATE entities
      SET item_count = item_count + 1
      WHERE id = NEW.from_id;
    END IF;
    RETURN NEW;
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- TRIGGERS
-- ============================================

CREATE TRIGGER trigger_update_item_count_insert
  AFTER INSERT ON relationships
  FOR EACH ROW
  EXECUTE FUNCTION update_entity_item_count();

CREATE TRIGGER trigger_update_item_count_delete
  AFTER DELETE ON relationships
  FOR EACH ROW
  EXECUTE FUNCTION update_entity_item_count();

CREATE TRIGGER trigger_update_item_count_update
  AFTER UPDATE OF from_id ON relationships
  FOR EACH ROW
  WHEN (OLD.from_id IS DISTINCT FROM NEW.from_id)
  EXECUTE FUNCTION update_entity_item_count();

-- ============================================
-- BACKFILL EXISTING COUNTS
-- ============================================

UPDATE entities e
SET item_count = (
  SELECT COUNT(*)
  FROM relationships r
  WHERE r.from_id = e.id
);

-- Add comment for GraphQL documentation
COMMENT ON COLUMN entities.item_count IS 'Number of direct child items/relationships. Automatically maintained by trigger.';
