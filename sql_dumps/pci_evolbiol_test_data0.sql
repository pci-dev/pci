TRUNCATE auth_user CASCADE;
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (1, 'test', 'dude', 'pci@inra.fr',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO public.auth_group (id, role, description) VALUES (2, 'recommender', '');
INSERT INTO public.auth_group (id, role, description) VALUES (3, 'manager', '');
INSERT INTO public.auth_group (id, role, description) VALUES (4, 'administrator', '');
INSERT INTO public.auth_group (id, role, description) VALUES (5, 'developper', '');
SELECT pg_catalog.setval('public.auth_group_id_seq', 7, true);
SELECT setval('public.auth_user_id_seq', 2, true);
INSERT INTO auth_membership (user_id, group_id) SELECT 1, id FROM auth_group;
INSERT INTO t_thematics (keyword) VALUES ('TEST');

-- apply migration step 2021-05-21 (sql_changes_synthesis.sql)
ALTER TABLE public.auth_user ADD COLUMN IF NOT EXISTS website VARCHAR(1024);

\i sql_dumps/insert_default_help_texts.sql
\i sql_dumps/insert_default_mail_templates.sql
