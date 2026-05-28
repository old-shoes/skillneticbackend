CREATE TABLE IF NOT EXISTS tutorial_categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(50) NOT NULL,
  slug VARCHAR(80) NOT NULL UNIQUE,
  icon VARCHAR(80) NOT NULL,
  color VARCHAR(50) NOT NULL DEFAULT 'blue',
  description VARCHAR(255) NOT NULL DEFAULT '',
  tutorial_count INTEGER NOT NULL DEFAULT 0,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tutorial_categories_enabled_sort
ON tutorial_categories (is_enabled, sort_order);

CREATE TABLE IF NOT EXISTS tutorial_tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(50) NOT NULL,
  slug VARCHAR(80) NOT NULL UNIQUE,
  tutorial_count INTEGER NOT NULL DEFAULT 0,
  is_hot BOOLEAN NOT NULL DEFAULT FALSE,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tutorial_tags_hot_enabled
ON tutorial_tags (is_hot, is_enabled, sort_order);

CREATE INDEX IF NOT EXISTS idx_tutorial_tags_slug
ON tutorial_tags (slug);

ALTER TABLE tutorials
ADD COLUMN IF NOT EXISTS cover_icon VARCHAR(80),
ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES tutorial_categories(id),
ADD COLUMN IF NOT EXISTS difficulty VARCHAR(30) NOT NULL DEFAULT 'beginner',
ADD COLUMN IF NOT EXISTS read_time_minutes INTEGER NOT NULL DEFAULT 10,
ADD COLUMN IF NOT EXISTS view_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS favorite_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS like_count INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS content_markdown TEXT NOT NULL DEFAULT '',
ADD COLUMN IF NOT EXISTS learning_points JSONB NOT NULL DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS suitable_for JSONB NOT NULL DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS search_keywords TEXT,
ADD COLUMN IF NOT EXISTS seo_title VARCHAR(160),
ADD COLUMN IF NOT EXISTS seo_description VARCHAR(300);

ALTER TABLE tutorials
ALTER COLUMN title TYPE VARCHAR(160),
ALTER COLUMN slug TYPE VARCHAR(180),
ALTER COLUMN summary TYPE VARCHAR(500);

CREATE INDEX IF NOT EXISTS idx_tutorials_status_published
ON tutorials (status, published_at DESC);

CREATE INDEX IF NOT EXISTS idx_tutorials_category_status
ON tutorials (category_id, status);

CREATE INDEX IF NOT EXISTS idx_tutorials_difficulty_status
ON tutorials (difficulty, status);

CREATE INDEX IF NOT EXISTS idx_tutorials_hot_status
ON tutorials (view_count DESC, favorite_count DESC);

CREATE INDEX IF NOT EXISTS idx_tutorials_slug_status
ON tutorials (slug, status);

CREATE TABLE IF NOT EXISTS tutorial_tag_relations (
  tutorial_id UUID NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES tutorial_tags(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tutorial_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_tutorial_tag_relations_tutorial
ON tutorial_tag_relations (tutorial_id);

CREATE INDEX IF NOT EXISTS idx_tutorial_tag_relations_tag
ON tutorial_tag_relations (tag_id);

CREATE TABLE IF NOT EXISTS tutorial_prompt_blocks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tutorial_id UUID NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
  title VARCHAR(120) NOT NULL,
  description VARCHAR(255),
  content TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tutorial_prompt_blocks_tutorial_sort
ON tutorial_prompt_blocks (tutorial_id, sort_order);

CREATE TABLE IF NOT EXISTS tutorial_related_items (
  tutorial_id UUID NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
  related_tutorial_id UUID NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (tutorial_id, related_tutorial_id)
);

CREATE INDEX IF NOT EXISTS idx_tutorial_related_items_tutorial
ON tutorial_related_items (tutorial_id, sort_order);

CREATE TABLE IF NOT EXISTS admin_operation_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  operator_id UUID,
  operator_name VARCHAR(80),
  module VARCHAR(80) NOT NULL,
  action VARCHAR(80) NOT NULL,
  target_id UUID,
  target_title VARCHAR(160),
  before_data JSONB,
  after_data JSONB,
  ip VARCHAR(80),
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_operation_logs_operator_time
ON admin_operation_logs (operator_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_operation_logs_module_action_time
ON admin_operation_logs (module, action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_operation_logs_target
ON admin_operation_logs (target_id);

CREATE TABLE IF NOT EXISTS learning_paths (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(120) NOT NULL,
  slug VARCHAR(120) NOT NULL UNIQUE,
  description VARCHAR(255) NOT NULL,
  icon VARCHAR(80) NOT NULL,
  tutorial_count INTEGER NOT NULL DEFAULT 0,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_learning_paths_enabled_sort
ON learning_paths (is_enabled, sort_order);
