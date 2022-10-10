ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS validation_timestamp timestamp without time zone;

ALTER TABLE "t_recommendations"
ADD COLUMN IF NOT EXISTS validation_timestamp timestamp without time zone;
