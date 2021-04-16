ALTER TABLE public.t_articles DISABLE TRIGGER auto_last_status_change_trigger;
ALTER TABLE public.t_articles DISABLE TRIGGER distinct_words_trigger;

ALTER TABLE "t_articles"
  ADD COLUMN "report_stage" VARCHAR(128),
  ADD COLUMN "scheduled_submission_date" date,
  ADD COLUMN "art_stage_1_id" integer,
  ADD FOREIGN KEY ("art_stage_1_id") REFERENCES "public"."t_articles"("id") ON DELETE SET NULL;
  -- ALTER TABLE "t_articles" ADD COLUMN "scheduled_submission_date" date;

ALTER TABLE public.t_articles ENABLE TRIGGER auto_last_status_change_trigger;
ALTER TABLE public.t_articles ENABLE TRIGGER distinct_words_trigger;

CREATE TABLE IF NOT EXISTS "t_report_survey" (
    "id" SERIAL PRIMARY KEY,
    "article_id" INTEGER REFERENCES "t_articles" ("id") ON DELETE CASCADE,
    "q1" VARCHAR(1024),
    "q2" VARCHAR(1024),
    "q3" VARCHAR(1024),
    "q4" BOOLEAN,
    "q5" TEXT,
    "q6" VARCHAR(1024),
    "q7" VARCHAR(1024),
    "q8" VARCHAR(1024),
    "q9" VARCHAR(1024),
    "q10" DATE,
    "q11" VARCHAR(128),
    "q11_details" TEXT,
    "q12" VARCHAR(128),
    "q12_details" TEXT,
    "q13" VARCHAR(512),
    "q13_details" TEXT,
    "q14" BOOLEAN,
    "q15" TEXT,
    "q16" VARCHAR(128),
    "q17" VARCHAR(128),
    "q18" BOOLEAN,
    "q19" BOOLEAN,
    "q20" VARCHAR(128),
    "q21" VARCHAR(128),
    "q22" VARCHAR(128),
    "q23" VARCHAR(128),
    "q24" DATE,
    "q24_1" VARCHAR(128),
    "q24_1_details" TEXT,
    "q25" BOOLEAN,
    "q26" VARCHAR(512),
    "q26_details" TEXT,
    "q27" VARCHAR(512),
    "q27_details" TEXT,
    "q28" VARCHAR(512),
    "q28_details" TEXT,
    "q29" BOOLEAN,
    "q30" VARCHAR(256),
    "q31" VARCHAR(128),
    "temp_art_stage_1_id" integer
);

ALTER TABLE "t_report_survey"
    ADD FOREIGN KEY ("temp_art_stage_1_id") REFERENCES "t_articles"("id") ON DELETE SET NULL;


ALTER TABLE "t_articles"
  ADD COLUMN "sub_thematics" VARCHAR(128);


ALTER TABLE "t_articles"
  ADD COLUMN "record_url_version" VARCHAR(128),
  ADD COLUMN "record_id_version" VARCHAR(128);