CREATE TYPE duration AS ENUM('Two weeks', 'Three weeks', 'Four weeks', 'Five weeks', 'Six weeks', 'Seven weeks', 'Eight weeks');

ALTER TABLE "t_reviews"
ADD COLUMN  IF NOT EXISTS review_duration duration DEFAULT 'Three weeks';
