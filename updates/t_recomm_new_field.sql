ALTER TABLE "t_recommendations"
ADD COLUMN IF NOT EXISTS author_last_change timestamp without time zone DEFAULT statement_timestamp();
