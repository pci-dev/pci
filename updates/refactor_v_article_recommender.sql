DROP VIEW v_article_recommender;
CREATE OR REPLACE VIEW v_article_recommender AS
SELECT
	r.article_id AS id,
	r.id AS recommendation_id,
	(au.first_name || ' ' || au.last_name) AS recommender
FROM (
	t_recommendations r
	LEFT JOIN auth_user au ON (r.recommender_id = au.id)
)
WHERE r.id in (select max(id) from t_recommendations group by article_id)
;

CREATE OR REPLACE VIEW v_article AS
SELECT
	a.*,
	r.recommender,
	rev.reviewers,
	to_char(a.upload_timestamp, 'YYYY-MM-DD HH24:MI:SS') as submission_date
FROM
	t_articles a
	JOIN v_article_recommender r ON a.id = r.id
	JOIN v_reviewers rev ON rev.id = r.recommendation_id
;
