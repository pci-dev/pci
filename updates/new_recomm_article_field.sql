ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  article_author character varying(512);

ALTER TABLE "t_recommendations"
ADD COLUMN IF NOT EXISTS  recommender_details character varying(512);
