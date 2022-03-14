ALTER TABLE "t_articles"
ADD COLUMN  IF NOT EXISTS suggest_reviewers text;
