ALTER TABLE users
ADD COLUMN IF NOT EXISTS github_connected BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS auth_email_codes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) NOT NULL,
  scene VARCHAR(50) NOT NULL,
  code_hash VARCHAR(255) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'unused',
  send_ip VARCHAR(80),
  user_agent TEXT,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_email_codes_email_scene
ON auth_email_codes (email, scene, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_email_codes_expires
ON auth_email_codes (expires_at);

CREATE INDEX IF NOT EXISTS idx_auth_email_codes_status
ON auth_email_codes (status);

CREATE TABLE IF NOT EXISTS auth_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  event_type VARCHAR(80) NOT NULL,
  provider VARCHAR(50),
  email VARCHAR(255),
  ip VARCHAR(80),
  user_agent TEXT,
  success BOOLEAN NOT NULL DEFAULT TRUE,
  fail_reason VARCHAR(255),
  metadata JSON NOT NULL DEFAULT '{}'::json,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_logs_user
ON auth_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_logs_email
ON auth_logs (email, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_auth_logs_event_type
ON auth_logs (event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS password_reset_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  email VARCHAR(255) NOT NULL,
  email_code_id UUID REFERENCES auth_email_codes(id) ON DELETE SET NULL,
  reset_ip VARCHAR(80),
  user_agent TEXT,
  success BOOLEAN NOT NULL DEFAULT FALSE,
  fail_reason VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_password_reset_records_user
ON password_reset_records (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_password_reset_records_email
ON password_reset_records (email, created_at DESC);

CREATE TABLE IF NOT EXISTS user_auth_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider VARCHAR(50) NOT NULL,
  provider_user_id VARCHAR(255),
  email VARCHAR(255),
  password_hash VARCHAR(255),
  github_username VARCHAR(100),
  github_avatar_url VARCHAR(500),
  github_profile_url VARCHAR(500),
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  is_verified BOOLEAN NOT NULL DEFAULT FALSE,
  bound_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_used_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(provider, provider_user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_auth_accounts_user
ON user_auth_accounts (user_id);

CREATE INDEX IF NOT EXISTS idx_user_auth_accounts_provider_email
ON user_auth_accounts (provider, email);
