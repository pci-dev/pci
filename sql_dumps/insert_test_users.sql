-- define cypress tests users - sync with cypress/fixtures/users.json

INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (102, 'admin', 'dude', 'admin@pci.org',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (103, 'developer', 'dude', 'developer@pci.org',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (104, 'manager', 'dude', 'manager@pci.org',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (105, 'recommender', 'dude', 'recommender@pci.org',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (106, 'reviewer', 'dude', 'reviewer@pci.org',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (107, 'user', 'dude', 'user@pci.org',  'pbkdf2(1000,20,sha512)$b56e6bf0b451ecd9$ec6acc9e1ff7a307bfbe21bdafc543ac64e1cb17', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);

-- assign users roles
--
--  1 | recommender   |
--  2 | manager       |
--  3 | administrator |
--  4 | developper    |

insert into auth_membership ("user_id", "group_id") values (102, 3);
insert into auth_membership ("user_id", "group_id") values (103, 4);
insert into auth_membership ("user_id", "group_id") values (104, 2);
insert into auth_membership ("user_id", "group_id") values (105, 1);
insert into auth_membership ("user_id", "group_id") values (106, 1);
-- normal user (user_id=107) => no role assigned

SELECT setval('public.auth_user_id_seq', 107);
