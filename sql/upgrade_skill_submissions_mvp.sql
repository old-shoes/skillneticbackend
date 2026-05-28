CREATE TABLE IF NOT EXISTS skill_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submitter_id UUID NOT NULL,
  title VARCHAR(100) NOT NULL DEFAULT '',
  slug VARCHAR(140),
  summary VARCHAR(160) NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  category_id UUID REFERENCES categories(id),
  category_name VARCHAR(80),
  tags JSONB NOT NULL DEFAULT '[]'::jsonb,
  difficulty VARCHAR(30) NOT NULL DEFAULT 'beginner',
  estimated_time VARCHAR(50) NOT NULL DEFAULT '',
  cover_image VARCHAR(500),
  target_audience JSONB NOT NULL DEFAULT '[]'::jsonb,
  use_cases JSONB NOT NULL DEFAULT '[]'::jsonb,
  highlights JSONB NOT NULL DEFAULT '[]'::jsonb,
  prompt_role VARCHAR(100) NOT NULL DEFAULT '',
  system_prompt TEXT NOT NULL DEFAULT '',
  output_formats JSONB NOT NULL DEFAULT '[]'::jsonb,
  creativity NUMERIC(3,2) NOT NULL DEFAULT 0.7,
  precision NUMERIC(3,2) NOT NULL DEFAULT 0.6,
  output_language VARCHAR(50) NOT NULL DEFAULT 'zh-CN',
  output_length VARCHAR(80) NOT NULL DEFAULT '',
  example_inputs JSONB NOT NULL DEFAULT '[]'::jsonb,
  example_output JSONB NOT NULL DEFAULT '{}'::jsonb,
  usage_guide TEXT NOT NULL DEFAULT '',
  faqs JSONB NOT NULL DEFAULT '[]'::jsonb,
  submit_note VARCHAR(500),
  status VARCHAR(40) NOT NULL DEFAULT 'draft',
  quality_score INTEGER,
  review_comment TEXT,
  review_reason_code VARCHAR(80),
  reviewed_by UUID,
  reviewed_at TIMESTAMPTZ,
  approved_skill_id UUID REFERENCES skills(id),
  submitted_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_submitter
ON skill_submissions (submitter_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_status_time
ON skill_submissions (status, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_category
ON skill_submissions (category_id, status);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_reviewed_by
ON skill_submissions (reviewed_by, reviewed_at DESC);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_tags
ON skill_submissions USING GIN (tags);

CREATE INDEX IF NOT EXISTS idx_skill_submissions_deleted
ON skill_submissions (deleted_at);

CREATE TABLE IF NOT EXISTS skill_submission_variables (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID NOT NULL REFERENCES skill_submissions(id) ON DELETE CASCADE,
  variable_name VARCHAR(80) NOT NULL,
  variable_label VARCHAR(80) NOT NULL,
  placeholder VARCHAR(255) NOT NULL DEFAULT '',
  description VARCHAR(255) NOT NULL DEFAULT '',
  is_required BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_submission_variables_submission
ON skill_submission_variables (submission_id, sort_order);

CREATE TABLE IF NOT EXISTS skill_submission_examples (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID NOT NULL REFERENCES skill_submissions(id) ON DELETE CASCADE,
  title VARCHAR(120) NOT NULL DEFAULT '',
  example_input JSONB NOT NULL DEFAULT '{}'::jsonb,
  example_output JSONB NOT NULL DEFAULT '{}'::jsonb,
  usage_note TEXT NOT NULL DEFAULT '',
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_submission_examples_submission
ON skill_submission_examples (submission_id, sort_order);

CREATE TABLE IF NOT EXISTS skill_submission_review_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID NOT NULL REFERENCES skill_submissions(id) ON DELETE CASCADE,
  action VARCHAR(80) NOT NULL,
  operator_id UUID,
  operator_type VARCHAR(30) NOT NULL DEFAULT 'admin',
  operator_name VARCHAR(80),
  from_status VARCHAR(40),
  to_status VARCHAR(40),
  comment TEXT,
  reason_code VARCHAR(80),
  required_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
  before_data JSONB,
  after_data JSONB,
  ip VARCHAR(80),
  user_agent TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_submission_review_logs_submission
ON skill_submission_review_logs (submission_id, created_at DESC);

CREATE TABLE IF NOT EXISTS skill_submission_risk_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  submission_id UUID NOT NULL REFERENCES skill_submissions(id) ON DELETE CASCADE,
  check_type VARCHAR(80) NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'pending',
  result_message VARCHAR(255),
  detail JSONB NOT NULL DEFAULT '{}'::jsonb,
  checked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_skill_submission_risk_checks_submission
ON skill_submission_risk_checks (submission_id);

CREATE INDEX IF NOT EXISTS idx_skill_submission_risk_checks_type_status
ON skill_submission_risk_checks (check_type, status);
