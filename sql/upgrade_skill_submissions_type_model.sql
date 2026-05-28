ALTER TABLE skill_submissions
ADD COLUMN IF NOT EXISTS skill_type VARCHAR(30) NOT NULL DEFAULT 'prompt';

ALTER TABLE skill_submissions
ADD COLUMN IF NOT EXISTS recommended_models JSONB NOT NULL DEFAULT '[]'::jsonb;
