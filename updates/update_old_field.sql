UPDATE  "t_articles"
SET suggest_reviewers='||' WHERE suggest_reviewers IS NULL;

UPDATE  "t_articles"
SET competitors='||' WHERE competitors IS NULL;
