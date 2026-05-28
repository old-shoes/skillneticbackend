CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  nickname VARCHAR(80) NOT NULL,
  avatar_url VARCHAR(500),
  level VARCHAR(20) NOT NULL DEFAULT 'Lv1',
  locale VARCHAR(20) NOT NULL DEFAULT 'zh',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  token_hash VARCHAR(255) NOT NULL UNIQUE,
  user_agent TEXT,
  ip VARCHAR(80),
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user ON user_sessions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token_hash);
