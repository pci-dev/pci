ALTER TABLE "auth_user" 
ADD COLUMN "email_options" character varying(1024) DEFAULT '|Email to reviewers|Email to authors|'::character varying;
