DROP VIEW v_article;

ALTER TABLE t_articles ALTER COLUMN sub_thematics TYPE character varying(512);
ALTER TABLE t_articles ALTER COLUMN record_url_version TYPE character varying(512);
ALTER TABLE t_articles ALTER COLUMN record_id_version TYPE character varying(512);

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
