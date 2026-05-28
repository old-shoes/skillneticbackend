CREATE TABLE categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(50) NOT NULL,
  slug VARCHAR(80) NOT NULL UNIQUE,
  icon VARCHAR(50) NOT NULL,
  color VARCHAR(50) NOT NULL DEFAULT 'blue',
  description VARCHAR(255) NOT NULL DEFAULT '',
  skill_count INTEGER NOT NULL DEFAULT 0,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(120) NOT NULL,
  slug VARCHAR(160) NOT NULL UNIQUE,
  summary VARCHAR(300) NOT NULL,
  content TEXT,
  cover_icon VARCHAR(50),
  category_id UUID REFERENCES categories(id),
  difficulty VARCHAR(30) NOT NULL DEFAULT 'beginner',
  favorite_count INTEGER NOT NULL DEFAULT 0,
  view_count INTEGER NOT NULL DEFAULT 0,
  is_featured BOOLEAN NOT NULL DEFAULT FALSE,
  is_hot BOOLEAN NOT NULL DEFAULT FALSE,
  status VARCHAR(30) NOT NULL DEFAULT 'draft',
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE tags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(50) NOT NULL,
  slug VARCHAR(80) NOT NULL UNIQUE,
  type VARCHAR(30) NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE skill_tags (
  skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (skill_id, tag_id)
);

CREATE TABLE tutorials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(120) NOT NULL,
  slug VARCHAR(160) NOT NULL UNIQUE,
  summary VARCHAR(300) NOT NULL,
  content TEXT,
  cover_image VARCHAR(500),
  chapter_count INTEGER NOT NULL DEFAULT 1,
  duration_minutes INTEGER NOT NULL DEFAULT 10,
  is_beginner BOOLEAN NOT NULL DEFAULT TRUE,
  is_featured BOOLEAN NOT NULL DEFAULT FALSE,
  status VARCHAR(30) NOT NULL DEFAULT 'draft',
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE homepage_stats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_favorites INTEGER NOT NULL DEFAULT 10000,
  quality_templates INTEGER NOT NULL DEFAULT 2000,
  monthly_visits INTEGER NOT NULL DEFAULT 50000,
  beginner_tutorials INTEGER NOT NULL DEFAULT 30,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE tracking_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_name VARCHAR(80) NOT NULL,
  user_id UUID,
  anonymous_id VARCHAR(100),
  page_url VARCHAR(500) NOT NULL,
  referrer VARCHAR(500),
  target_type VARCHAR(50),
  target_id VARCHAR(100),
  extra JSONB NOT NULL DEFAULT '{}'::jsonb,
  ip VARCHAR(80),
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
