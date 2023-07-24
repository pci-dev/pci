ALTER TABLE "t_reviews"
ADD COLUMN IF NOT EXISTS suggested_reviewers_send boolean;
