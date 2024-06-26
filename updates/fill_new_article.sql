ALTER TABLE auth_user 
ADD COLUMN IF NOT EXISTS new_article_cache jsonb;
