CREATE TABLE "mail_templates"(
    "id" SERIAL PRIMARY KEY,
    "hashtag" VARCHAR(128),
    "lang" VARCHAR(10),
    "subject" VARCHAR(256),
    "contents" TEXT,
    "description" VARCHAR(512)
);