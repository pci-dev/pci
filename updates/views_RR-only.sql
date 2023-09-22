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
        SELECT DISTINCT recomm.id FROM t_articles art JOIN t_recommendations recomm ON art.id = recomm.article_id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id 
        LEFT JOIN (
                SELECT recommendation_id, COUNT(*) AS num_reviews
                FROM t_reviews
                GROUP BY recommendation_id
        ) rev ON recomm.id = rev.recommendation_id
        WHERE art.status = 'Under consideration'
            AND recomm.recommender_id = recommender.id
        GROUP BY recomm.id, art.report_stage, rev.num_reviews
        HAVING ((art.report_stage = 'STAGE 1' AND COALESCE(rev.num_reviews, 0) < 2) OR (art.report_stage = 'STAGE 2' AND COALESCE(rev.num_reviews, 0) = 0))
            UNION ALL
	    SELECT DISTINCT recomm.id FROM t_articles art JOIN t_recommendations recomm ON recomm.article_id = art.id JOIN t_reviews trev ON trev.recommendation_id = recomm.id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id LEFT JOIN t_reviews trew ON trew.recommendation_id = recomm.id AND trew.review_state = 'Awaiting review' WHERE art.status = 'Under consideration' AND recomm.recommender_id = recommender.id AND trev.review_state = 'Review completed' 
            GROUP BY recomm.id, art.id, recomm.recommender_id HAVING COUNT(trev.id) >= 2 AND SUM(CASE WHEN trew.id IS NULL THEN 0 ELSE 1 END) = 0) requiring_action_nb) AS requiring_action,
    (SELECT COALESCE(SUM(nb), 0) 
    FROM (SELECT COUNT(*) AS nb FROM t_articles art JOIN t_recommendations recomm ON art.id = recomm.article_id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id 
        LEFT JOIN (
                SELECT recommendation_id, COUNT(*) AS num_reviews
                FROM t_reviews
                GROUP BY recommendation_id
        ) rev ON recomm.id = rev.recommendation_id
        WHERE art.status = 'Under consideration'
            AND recomm.recommender_id = recommender.id
        GROUP BY recomm.id, art.report_stage, rev.num_reviews
        HAVING ((art.report_stage = 'STAGE 1' AND COALESCE(rev.num_reviews, 0) < 2) OR (art.report_stage = 'STAGE 2' AND COALESCE(rev.num_reviews, 0) = 0))
    ) subquery) AS requiring_reviewers,
    (SELECT COALESCE(SUM(nb), 0) FROM (SELECT COUNT(DISTINCT recomm.id) AS nb FROM t_articles art JOIN t_recommendations recomm ON recomm.article_id = art.id JOIN t_reviews trev ON trev.recommendation_id = recomm.id JOIN v_article_recommender v_art ON recomm.id = v_art.recommendation_id LEFT JOIN t_reviews trew ON trew.recommendation_id = recomm.id AND trew.review_state = 'Awaiting review' WHERE art.status = 'Under consideration' AND recomm.recommender_id = recommender.id AND trev.review_state = 'Review completed' 
            GROUP BY recomm.id, art.id, recomm.recommender_id HAVING COUNT(trev.id) >= 2 AND SUM(CASE WHEN trew.id IS NULL THEN 0 ELSE 1 END) = 0) subquery) AS required_reviews_completed,
    (SELECT COUNT(DISTINCT recomm.id) FROM t_articles art, t_reviews trev, t_recommendations recomm, v_article_recommender v_art WHERE recomm.article_id = art.id and trev.recommendation_id = recomm.id and recomm.recommender_id=recommender.id and recomm.id=v_art.recommendation_id and recomm.recommendation_state = 'Ongoing' and trev.review_state = 'Awaiting review' and trev.acceptation_timestamp + convert_duration_to_sql_interval(trev.review_duration) < NOW()) AS late_reviews
FROM 
(SELECT au.id FROM auth_user au, auth_membership am, auth_group ag WHERE au.id=am.user_id and am.group_id=ag.id and ag.role='recommender') recommender;
