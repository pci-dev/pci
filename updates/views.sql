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
    recommender.id AS id,
    (SELECT DISTINCT recommender_details  FROM t_recommendations  WHERE recommender_id=recommender.id),
    (SELECT COUNT(*) FROM t_suggested_recommenders WHERE suggested_recommender_id=recommender.id) AS total_invitations,
    (SELECT COUNT(*) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id=art.id and recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS total_accepted,
    (SELECT COUNT(*) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE art.id=recomm.article_id and art.status in ('Recommended', 'Recommended-private', 'Rejected', 'Cancelled') and art.report_stage in ('STAGE 1', 'STAGE 2') and  recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS total_completed,
    (SELECT COUNT(*) FROM t_articles art, t_suggested_recommenders sug WHERE sug.suggested_recommender_id=recommender.id and sug.declined='FALSE' and art.id=sug.article_id and art.status='Awaiting consideration') AS current_invitations,          
    (SELECT COUNT(*) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE art.id=recomm.article_id and art.status in ('Under consideration', 'Awaiting revision', 'Scheduled submission revision', 'Scheduled submission under consideration') and art.report_stage in ('STAGE 1', 'STAGE 2') and recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS current_assignments,
    (SELECT COUNT(*) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE art.id=recomm.article_id and art.status in ('Awaiting revision', 'Scheduled submission revision') and art.report_stage in ('STAGE 1', 'STAGE 2') and  recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS awaiting_revision,
    (SELECT COALESCE(SUM(nb), 0) FROM
		(
            SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations recomm, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = recomm.id and recomm.article_id = a.id and a.status = 'Under consideration' and ts.suggested_recommender_id=recommender.id GROUP BY a.id, ts.suggested_recommender_id HAVING (COUNT(trev.id) < 2 and a.report_stage = 'STAGE 1') or (COUNT(trev.id) = 0 and a.report_stage = 'STAGE 2')
			    UNION ALL
		    SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations recomm, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = recomm.id and recomm.article_id = a.id and ts.suggested_recommender_id=recommender.id GROUP BY a.id, ts.suggested_recommender_id HAVING COUNT(trev.id) filter (WHERE trev.acceptation_timestamp is not null) = COUNT(trev.id) filter (WHERE trev.review_state = 'Review completed')
	) requiring_action_nb) AS requiring_action,
    (SELECT COALESCE(SUM(nb), 0) FROM ((SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations recomm, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = recomm.id and recomm.article_id = a.id and a.status in ('Under consideration', 'Awaiting revision') and ts.suggested_recommender_id=recommender.id GROUP BY a.id, ts.suggested_recommender_id HAVING (COUNT(trev.id) < 2 and a.report_stage = 'STAGE 1') or (COUNT(trev.id) = 0 and a.report_stage = 'STAGE 2'))) subquery) AS requiring_reviewers,
    (SELECT COALESCE(SUM(nb), 0) FROM ((SELECT COUNT(*) AS nb FROM t_articles a , t_reviews trev, t_recommendations recomm, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = recomm.id and recomm.article_id = a.id and  a.status in ('Under consideration', 'Awaiting revision') and ts.suggested_recommender_id=recommender.id GROUP BY a.id, ts.suggested_recommender_id HAVING COUNT(trev.id) filter (WHERE trev.acceptation_timestamp is not null) = COUNT(trev.id) filter (WHERE trev.review_state = 'Review completed'))) subquery) AS required_reviews_completed,
    (SELECT COUNT(*) FROM t_articles a , t_reviews trev, t_recommendations recomm, t_suggested_recommenders ts WHERE ts.article_id = a.id and trev.recommendation_id = recomm.id and recomm.article_id = a.id and ts.suggested_recommender_id=recommender.id and trev.acceptation_timestamp + convert_duration_to_sql_interval(trev.review_duration) > NOW()) AS late_reviews
FROM 
(SELECT au.id FROM auth_user au, auth_membership am, auth_group ag WHERE au.id=am.user_id and am.group_id=ag.id and ag.role='recommender') recommender;
