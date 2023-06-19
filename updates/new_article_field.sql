ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  is_scheduled boolean DEFAULT false;

UPDATE "t_articles" 
SET is_scheduled = true WHERE status='Scheduled submission pending';
