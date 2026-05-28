ALTER TABLE skills
ADD COLUMN IF NOT EXISTS type VARCHAR(30) NOT NULL DEFAULT 'prompt',
ADD COLUMN IF NOT EXISTS use_case VARCHAR(120),
ADD COLUMN IF NOT EXISTS search_keywords TEXT,
ADD COLUMN IF NOT EXISTS recommended_models JSONB NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE tags
ADD COLUMN IF NOT EXISTS skill_count INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_skills_status_published
ON skills (status, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_skills_category_status
ON skills (category_id, status);

CREATE INDEX IF NOT EXISTS idx_skills_difficulty_status
ON skills (difficulty, status);

CREATE INDEX IF NOT EXISTS idx_skills_type_status
ON skills (type, status);

CREATE INDEX IF NOT EXISTS idx_skills_hot_status
ON skills (is_hot, status, favorite_count DESC);

CREATE INDEX IF NOT EXISTS idx_skills_featured_status
ON skills (is_featured, status, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_tags_type_enabled
ON tags (type, is_enabled, sort_order);

CREATE INDEX IF NOT EXISTS idx_tags_slug_type
ON tags (slug, type);

CREATE INDEX IF NOT EXISTS idx_skill_tags_skill
ON skill_tags (skill_id);

CREATE INDEX IF NOT EXISTS idx_skill_tags_tag
ON skill_tags (tag_id);
