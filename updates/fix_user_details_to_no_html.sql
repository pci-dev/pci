update t_reviews
set reviewer_details = flattened
from (
	select id as _id,
	regexp_replace(reviewer_details, '<[^>]+>', '', 'g') as flattened
	from t_reviews
	where reviewer_details ~ '<span>'
) as _
where id = _id;

update t_recommendations
set recommender_details = flattened
from (
	select id as _id,
	regexp_replace(recommender_details, '<[^>]+>', '', 'g') as flattened
	from t_recommendations
	where recommender_details ~ '<span>'
) as _
where id = _id;

update t_articles
set submitter_details = flattened
from (
	select id as _id,
	regexp_replace(submitter_details, '<[^>]+>', '', 'g') as flattened
	from t_articles
	where submitter_details ~ '<span>'
) as _
where id = _id;

update t_press_reviews
set contributor_details = flattened
from (
	select id as _id,
	regexp_replace(contributor_details, '<[^>]+>', '', 'g') as flattened
	from t_press_reviews
	where contributor_details ~ '<span>'
) as _
where id = _id;
