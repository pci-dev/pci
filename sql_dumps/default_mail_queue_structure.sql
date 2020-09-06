CREATE TABLE "mail_queue"(
    "id" SERIAL PRIMARY KEY,
    "sending_status" VARCHAR(128),
    "sending_attempts" INTEGER,
    "sending_date" TIMESTAMP,
    "dest_mail_address" VARCHAR(256),
    "user_id" INTEGER REFERENCES "auth_user" ("id") ON DELETE RESTRICT,
    "recommendation_id" INTEGER REFERENCES "t_recommendations" ("id") ON DELETE CASCADE,
    "mail_subject" VARCHAR(256),
    "mail_content" TEXT,
    "mail_template_hashtag" VARCHAR(128)
);