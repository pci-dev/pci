ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS doi_of_published_article character varying(512);
