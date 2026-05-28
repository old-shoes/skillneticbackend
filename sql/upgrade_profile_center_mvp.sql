ALTER TABLE users
ADD COLUMN IF NOT EXISTS bio VARCHAR(300),
ADD COLUMN IF NOT EXISTS location VARCHAR(80),
ADD COLUMN IF NOT EXISTS points INTEGER NOT NULL DEFAULT 0,
ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(80);

CREATE INDEX IF NOT EXISTS idx_users_points
ON users(points DESC);

CREATE INDEX IF NOT EXISTS idx_users_created_at
ON users(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_users_deleted_at
ON users(deleted_at);

CREATE TABLE IF NOT EXISTS user_favorites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_type VARCHAR(50) NOT NULL,
  target_id UUID NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(user_id, target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_user_favorites_user
ON user_favorites(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_favorites_target
ON user_favorites(target_type, target_id);

CREATE TABLE IF NOT EXISTS user_point_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  event_type VARCHAR(80) NOT NULL,
  points_change INTEGER NOT NULL,
  points_before INTEGER NOT NULL,
  points_after INTEGER NOT NULL,
  related_type VARCHAR(80),
  related_id UUID,
  description VARCHAR(255),
  dedup_key VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_point_logs_user
ON user_point_logs(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_point_logs_event
ON user_point_logs(event_type, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS idx_user_point_logs_dedup_key
ON user_point_logs(dedup_key)
WHERE dedup_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS user_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type VARCHAR(80) NOT NULL,
  title VARCHAR(120) NOT NULL,
  content TEXT,
  related_type VARCHAR(80),
  related_id UUID,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_notifications_user
ON user_notifications(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_notifications_unread
ON user_notifications(user_id, is_read, created_at DESC);

CREATE TABLE IF NOT EXISTS help_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(120) NOT NULL,
  content TEXT NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'published',
  points_cost INTEGER NOT NULL DEFAULT 5,
  reply_count INTEGER NOT NULL DEFAULT 0,
  view_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_help_posts_user
ON help_posts(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_help_posts_status
ON help_posts(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_submitter_status
ON skill_submissions(submitter_id, status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_submitter_updated
ON skill_submissions(submitter_id, updated_at DESC);
