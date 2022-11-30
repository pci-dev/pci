ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  preprint_server character varying(512);
