ALTER TABLE "auth_user"
  ADD COLUMN "recover_email" character varying(512),
  ADD COLUMN "recover_email_key" character varying(512),
  ADD UNIQUE ("recover_email"),
  ADD UNIQUE ("recover_email_key");
