TRUNCATE auth_user CASCADE;
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (1, 'Sylvain', 'Piry', 'piry@supagro.fr',  'pbkdf2(1000,20,sha512)$8aef05bd8a5b0262$a985f8cfeffe19b3d7637a6d79b67fc13db47521', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO public.auth_group (id, role, description) VALUES (2, 'recommender', '');
INSERT INTO public.auth_group (id, role, description) VALUES (3, 'manager', '');
INSERT INTO public.auth_group (id, role, description) VALUES (4, 'administrator', '');
INSERT INTO public.auth_group (id, role, description) VALUES (5, 'developper', '');
SELECT pg_catalog.setval('public.auth_group_id_seq', 7, true);
SELECT setval('public.auth_user_id_seq', 2, true);
INSERT INTO auth_membership (user_id, group_id) SELECT 1, id FROM auth_group;
INSERT INTO t_thematics (keyword) VALUES ('TEST');


\i sql_dumps/insert_default_help_texts.sql
\i sql_dumps/insert_default_mail_templates.sql
