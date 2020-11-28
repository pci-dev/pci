UPDATE t_reviews SET review_state = 'Review completed' WHERE review_state = 'Completed';
UPDATE t_reviews SET review_state = 'Willing to review' WHERE review_state = 'Ask to review';
UPDATE t_reviews SET review_state = 'Awaiting review' WHERE review_state = 'Under consideration';
UPDATE t_reviews SET review_state = 'Awaiting response' WHERE review_state = 'Pending';
