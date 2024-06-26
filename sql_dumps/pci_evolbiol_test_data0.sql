TRUNCATE auth_user CASCADE;
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved", "website", "no_orcid", "keywords") VALUES (1, 'test', 'dude', 'test@pci.org',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', 'Never', '|TEST|', 'expertise', NULL, '2016-11-03 13:17:38', TRUE, 'no-website', TRUE, 'test');
INSERT INTO public.auth_group (role, description) VALUES ('recommender', '');
INSERT INTO public.auth_group (role, description) VALUES ('manager', '');
INSERT INTO public.auth_group (role, description) VALUES ('administrator', '');
INSERT INTO public.auth_group (role, description) VALUES ('developer', '');
SELECT setval('public.auth_user_id_seq', 1);
INSERT INTO auth_membership (user_id, group_id) SELECT 1, id FROM auth_group;
INSERT INTO t_thematics (keyword) VALUES ('TEST');
