ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS validation_timestamp timestamp without time zone;

ALTER TABLE "t_recommendations"
ADD COLUMN IF NOT EXISTS validation_timestamp timestamp without time zone;

UPDATE t_recommendations
SET validation_timestamp = t_articles.last_status_change
FROM t_articles
WHERE t_recommendations.article_id = t_articles.id 
AND recommendation_state = 'Recommended';
