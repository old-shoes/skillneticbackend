ALTER TABLE tutorial_categories
ADD COLUMN IF NOT EXISTS category_group VARCHAR(80),
ADD COLUMN IF NOT EXISTS scene VARCHAR(80),
ADD COLUMN IF NOT EXISTS difficulty VARCHAR(30),
ADD COLUMN IF NOT EXISTS skill_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS is_hot BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS created_by UUID,
ADD COLUMN IF NOT EXISTS updated_by UUID;

CREATE INDEX IF NOT EXISTS idx_tutorial_categories_group
ON tutorial_categories (category_group, is_enabled, sort_order);

CREATE INDEX IF NOT EXISTS idx_tutorial_categories_scene
ON tutorial_categories (scene, is_enabled);

CREATE INDEX IF NOT EXISTS idx_tutorial_categories_difficulty
ON tutorial_categories (difficulty, is_enabled);

CREATE INDEX IF NOT EXISTS idx_tutorial_categories_hot
ON tutorial_categories (is_hot, is_enabled, sort_order);

CREATE INDEX IF NOT EXISTS idx_tutorial_categories_deleted
ON tutorial_categories (deleted_at);
