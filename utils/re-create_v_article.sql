DROP VIEW v_article;
CREATE VIEW v_article AS
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
