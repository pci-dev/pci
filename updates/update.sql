update t_reviews set reviewer_details = null
where reviewer_details is not null and reviewer_id is not null;
