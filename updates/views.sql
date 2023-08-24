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
    (SELECT COUNT(DISTINCT id) FROM (
        SELECT DISTINCT art.id FROM t_articles art,  t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and recomm.recommender_id=recommender.id and recomm.id=v_art.recommendation_id 
		    UNION ALL
	    SELECT DISTINCT art.id FROM t_articles art, t_suggested_recommenders ts WHERE ts.suggested_recommender_id=recommender.id and ts.article_id = art.id ) total_invitations_nb) AS total_invitations,
    (SELECT COUNT(recomm.id) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id=art.id and recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS total_accepted,
    (SELECT COUNT(recomm.id) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE art.id=recomm.article_id and art.status in ('Recommended', 'Recommended-private', 'Rejected', 'Cancelled') and art.report_stage in ('STAGE 1', 'STAGE 2') and  recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS total_completed,
    (SELECT COUNT(art.id) FROM t_articles art, t_suggested_recommenders sug WHERE sug.suggested_recommender_id=recommender.id and sug.declined='FALSE' and art.id=sug.article_id and art.status='Awaiting consideration') AS current_invitations,          
    (SELECT COUNT(recomm.id) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE art.id=recomm.article_id and art.status in ('Under consideration', 'Awaiting revision', 'Scheduled submission revision', 'Scheduled submission under consideration') and art.report_stage in ('STAGE 1', 'STAGE 2') and recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS current_assignments,
    (SELECT COUNT(recomm.id) FROM t_articles art, t_recommendations recomm, v_article_recommender v_art WHERE art.id=recomm.article_id and art.status in ('Awaiting revision', 'Scheduled submission revision') and art.report_stage in ('STAGE 1', 'STAGE 2') and  recomm.recommender_id=recommender.id and recomm.id = v_art.recommendation_id) AS awaiting_revision,
    (SELECT COUNT(DISTINCT id) FROM (
        SELECT DISTINCT recomm.id FROM t_articles art, t_reviews trev, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and trev.recommendation_id = recomm.id and art.status = 'Under consideration' and recomm.recommender_id=recommender.id and recomm.id=v_art.recommendation_id GROUP BY recomm.id, art.id, recomm.recommender_id HAVING (COUNT(trev.id) < 2 and art.report_stage = 'STAGE 1') or (COUNT(trev.id) = 0 and art.report_stage = 'STAGE 2')
		    UNION ALL
	    SELECT DISTINCT recomm.id FROM t_articles art, t_reviews trev, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and trev.recommendation_id = recomm.id and art.status in ('Under consideration', 'Awaiting revision') and recomm.recommender_id=recommender.id and recomm.id=v_art.recommendation_id and trev.review_state = 'Review completed' GROUP BY recomm.id, art.id, recomm.recommender_id HAVING COUNT(trev.id) >= 2) requiring_action_nb) AS requiring_action,
    (SELECT COALESCE(SUM(nb), 0) FROM ((SELECT COUNT(*) AS nb FROM t_articles art, t_reviews trev, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and trev.recommendation_id = recomm.id  and art.status = 'Under consideration' and recomm.recommender_id=recommender.id and recomm.id=v_art.recommendation_id GROUP BY art.id, recomm.recommender_id HAVING (COUNT(trev.id) < 2 and art.report_stage = 'STAGE 1') or (COUNT(trev.id) = 0 and art.report_stage = 'STAGE 2'))) subquery) AS requiring_reviewers,
    (SELECT COALESCE(SUM(nb), 0) FROM ((SELECT COUNT(DISTINCT recomm.id) AS nb FROM t_articles art, t_reviews trev, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and trev.recommendation_id = recomm.id  and  art.status in ('Under consideration', 'Awaiting revision') and recomm.recommender_id=recommender.id and recomm.id=v_art.recommendation_id and trev.review_state = 'Review completed' GROUP BY recomm.id, art.id, recomm.recommender_id HAVING COUNT(trev.id) >= 2)) subquery) AS required_reviews_completed,
    (SELECT COUNT(DISTINCT recomm.id) FROM t_articles art, t_reviews trev, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and trev.recommendation_id = recomm.id and recomm.recommender_id=recommender.id and recomm.id=v_art.recommendation_id and trev.acceptation_timestamp + convert_duration_to_sql_interval(trev.review_duration) > NOW()) AS late_reviews
FROM 
(SELECT au.id FROM auth_user au, auth_membership am, auth_group ag WHERE au.id=am.user_id and am.group_id=ag.id and ag.role='recommender') recommender;
