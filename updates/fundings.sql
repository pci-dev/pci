ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  funding character varying(1024) DEFAULT '';
