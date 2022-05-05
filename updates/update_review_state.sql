UPDATE "t_reviews"
SET "review_state" = 'Cancelled' WHERE "reviewer_id" IS NULL;
