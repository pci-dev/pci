ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  article_submitter character varying(512);

ALTER TABLE "t_recommendations"
ADD COLUMN IF NOT EXISTS  recommender_details character varying(512);

ALTER TABLE "t_press_reviews"
ADD COLUMN IF NOT EXISTS  corecommender_details character varying(512);
