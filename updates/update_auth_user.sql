ALTER TABLE auth_user RENAME column registration_id to sso_id;
ALTER TABLE auth_user RENAME column registration_key to action_token;
ALTER TABLE auth_user ADD column if not exists last_password_change timestamp without time zone;
