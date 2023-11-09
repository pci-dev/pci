ALTER TABLE "auth_user" 
ADD COLUMN IF NOT EXISTS orcid varchar(16);
