ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS manager_authors text DEFAULT '';
