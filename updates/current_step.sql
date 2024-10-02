BEGIN;

LOCK TABLE t_articles IN ACCESS EXCLUSIVE MODE;
LOCK TABLE v_article IN ACCESS EXCLUSIVE MODE;

ALTER TABLE t_articles
ADD COLUMN IF NOT EXISTS current_step text;

COMMIT;
