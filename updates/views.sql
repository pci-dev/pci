CREATE OR REPLACE FUNCTION convert_duration_to_sql_interval(d duration)
RETURNS INTERVAL AS $$
DECLARE sql_interval INTERVAL;
BEGIN
    sql_interval :=
    CASE d
        WHEN 'Two weeks' THEN '2 weeks'
        WHEN 'Three weeks' THEN '3 weeks'
        WHEN 'Four weeks' THEN '4 weeks'
        WHEN 'Five weeks' THEN '5 weeks'
        WHEN 'Six weeks' THEN '6 weeks'
        WHEN 'Seven weeks' THEN '7 weeks'
        WHEN 'Eight weeks' THEN '8 weeks'
        ELSE NULL
    END;
    RETURN sql_interval;
END;
$$ LANGUAGE plpgsql;


DROP VIEW IF EXISTS v_recommender_stats;
CREATE OR REPLACE VIEW v_recommender_stats AS
SELECT 
    r.suggested_recommender_id AS id,
    (SELECT DISTINCT recommender_details  FROM t_recommendations  WHERE recommender_id=r.suggested_recommender_id),
    (SELECT COUNT(*) FROM t_suggested_recommenders WHERE suggested_recommender_id=r.suggested_recommender_id) AS total_invitations,
    (SELECT COUNT(*) FROM t_recommendations recomm, t_suggested_recommenders sug WHERE sug.suggested_recommender_id=recomm.recommender_id and sug.declined='FALSE' and  sug.suggested_recommender_id=r.suggested_recommender_id and recomm.article_id = sug.article_id ) AS total_accepted,
    (SELECT COUNT(*) FROM t_articles a, t_recommendations trec WHERE a.id=trec.article_id and a.status in ('Recommended', 'Recommended-private', 'Rejected', 'Cancelled') and a.report_stage in ('STAGE 1', 'STAGE 2') and  trec.recommender_id=r.suggested_recommender_id) AS total_completed,
    (SELECT COUNT(*) FROM t_articles a , t_suggested_recommenders ts WHERE ts.suggested_recommender_id=r.suggested_recommender_id and ts.declined='FALSE' and a.id=ts.article_id and a.status='Awaiting consideration') AS current_invitations,          
    (SELECT COUNT(status) FROM t_articles a, t_suggested_recommenders ts WHERE ts.article_id = a.id and a.status in ('Under consideration', 'Awaiting revision') and a.report_stage in ('STAGE 1', 'STAGE 2') and  ts.suggested_recommender_id=r.suggested_recommender_id) AS current_assignments,
    (SELECT COUNT(status) FROM t_articles a, t_suggested_recommenders ts WHERE ts.article_id = a.id and a.status='Awaiting revision' and a.report_stage in ('STAGE 1', 'STAGE 2') and  ts.suggested_recommender_id=r.suggested_recommender_id) AS awaiting_revision,
    (SELECT COALESCE(SUM(nb), 0) FROM
		(
            SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations trec, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = trec.id and trec.article_id = a.id and a.status = 'Under consideration' and ts.suggested_recommender_id=r.suggested_recommender_id GROUP BY a.id, ts.suggested_recommender_id HAVING (COUNT(trev.id) < 2 and a.report_stage = 'STAGE 1') or (COUNT(trev.id) = 0 and a.report_stage = 'STAGE 2')
			    UNION ALL
		    SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations trec, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = trec.id and trec.article_id = a.id and ts.suggested_recommender_id=r.suggested_recommender_id GROUP BY a.id, ts.suggested_recommender_id HAVING COUNT(trev.id) filter (WHERE trev.acceptation_timestamp is not null) = COUNT(trev.id) filter (WHERE trev.review_state = 'Review completed')
	) requiring_action_nb) AS requiring_action,
    (SELECT COALESCE(SUM(nb), 0) FROM ((SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations trec, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = trec.id and trec.article_id = a.id and a.status in ('Under consideration', 'Awaiting revision') and ts.suggested_recommender_id=r.suggested_recommender_id GROUP BY a.id, ts.suggested_recommender_id HAVING (COUNT(trev.id) < 2 and a.report_stage = 'STAGE 1') or (COUNT(trev.id) = 0 and a.report_stage = 'STAGE 2'))) subquery) AS requiring_reviewers,
    (SELECT COALESCE(SUM(nb), 0) FROM ((SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations trec, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = trec.id and trec.article_id = a.id and  a.status in ('Under consideration', 'Awaiting revision') and ts.suggested_recommender_id=r.suggested_recommender_id GROUP BY a.id, ts.suggested_recommender_id HAVING COUNT(trev.id) filter (WHERE trev.acceptation_timestamp is not null) = COUNT(trev.id) filter (WHERE trev.review_state = 'Review completed'))) subquery) AS required_reviews_completed,
    (SELECT COUNT(*) FROM t_articles a , t_reviews trev, t_recommendations trec, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = trec.id and trec.article_id = a.id and ts.suggested_recommender_id=r.suggested_recommender_id and trev.acceptation_timestamp + convert_duration_to_sql_interval(trev.review_duration) > NOW()) AS late_reviews
FROM 
(SELECT DISTINCT suggested_recommender_id FROM t_suggested_recommenders) r;
