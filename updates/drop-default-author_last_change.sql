ALTER TABLE t_recommendations ALTER author_last_change DROP DEFAULT;
UPDATE t_recommendations SET author_last_change = NULL;
