-- Remove the redundant 'series' attribute from Pokemon TCG sets
-- The series hierarchy is now defined via relationships, not attributes
-- This affects 169 sets

UPDATE entities
SET attributes = attributes - 'series'
WHERE attributes ? 'series';
