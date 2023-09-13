ALTER TABLE "auth_user" 
ADD COLUMN "email_options" character varying(1024) DEFAULT '||'::character varying;
