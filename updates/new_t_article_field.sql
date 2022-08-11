ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS request_submission_change boolean DEFAULT false;
