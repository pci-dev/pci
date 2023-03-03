CREATE OR REPLACE VIEW v_postprint_recommendations AS
SELECT 
    r.id AS id, 
    r.last_change, 
    r.article_id, 
    r.doi, 
    r.is_closed, 
    r.recommendation_state, 
    r.recommender_id, 
    r.recommendation_timestamp, 
    r.recommendation_comments, 
    r.recommender_details,
    a.already_published, 
    a.status, 
    a.report_stage,
    a.art_stage_1_id, 
    a.scheduled_submission_date
FROM 
    t_recommendations r,
    t_articles a 
WHERE 
    r.article_id = a.id 
AND a.already_published=true
AND r.id in (select max(id) from t_recommendations group by article_id)
;

CREATE OR REPLACE VIEW v_preprint_recommendations AS
SELECT 
    r.id AS id, 
    r.last_change, 
    r.article_id, 
    r.doi, 
    r.is_closed, 
    r.recommendation_state, 
    r.recommender_id, 
    r.recommendation_timestamp, 
    r.recommendation_comments, 
    r.recommender_details,
    a.already_published, 
    a.status, 
    a.report_stage,
    a.art_stage_1_id, 
    a.scheduled_submission_date
FROM 
    t_recommendations r,
    t_articles a 
WHERE 
    r.article_id = a.id 
AND a.already_published=false
AND a.status IN ('Under consideration', 'Scheduled submission under consideration')
AND r.id in (select max(id) from t_recommendations group by article_id)
;
