ALTER TABLE "auth_user" 
ADD COLUMN IF NOT EXISTS no_orcid boolean DEFAULT(FALSE) NOT NULL;
