ALTER TABLE "t_articles"
  ADD COLUMN "report_stage" VARCHAR(128),
  ADD COLUMN "art_stage_1_id" integer,
  ADD FOREIGN KEY ("art_stage_1_id") REFERENCES "public"."t_articles"("id") ON DELETE SET NULL;
  
ALTER TABLE "t_articles" ADD COLUMN "scheduled_submission_date" date;

CREATE TABLE IF NOT EXISTS "t_report_survey" (
    "id" SERIAL PRIMARY KEY,
    "article_id" INTEGER REFERENCES "t_articles" ("id") ON DELETE CASCADE,
    "Q1" VARCHAR(1024),
    "Q2" VARCHAR(1024),
    "Q3" VARCHAR(1024),
    "Q4" BOOLEAN,
    "Q5" TEXT,
    "Q6" VARCHAR(1024),
    "Q7" VARCHAR(1024),
    "Q8" VARCHAR(1024),
    "Q9" VARCHAR(1024),
    "Q10" DATE,
    "Q11" VARCHAR(128),
    "Q11_details" TEXT,
    "Q12" VARCHAR(128),
    "Q12_details" TEXT,
    "Q13" VARCHAR(512),
    "Q13_details" TEXT,
    "Q14" BOOLEAN,
    "Q15" TEXT,
    "Q16" VARCHAR(128),
    "Q17" VARCHAR(128),
    "Q18" BOOLEAN,
    "Q19" BOOLEAN,
    "Q20" VARCHAR(128),
    "Q21" VARCHAR(128),
    "Q22" VARCHAR(128),
    "Q23" VARCHAR(128),
    "Q24" DATE,
    "Q24_1" VARCHAR(128),
    "Q24_1_details" TEXT,
    "Q25" BOOLEAN,
    "Q26" VARCHAR(512),
    "Q26_details" TEXT,
    "Q27" VARCHAR(512),
    "Q27_details" TEXT,
    "Q28" VARCHAR(512),
    "Q28_details" TEXT,
    "Q29" BOOLEAN,
    "Q30" VARCHAR(256),
    "Q31" VARCHAR(128),
    "temp_art_stage_1_id" integer
);

ALTER TABLE "t_report_survey"
    ADD FOREIGN KEY ("temp_art_stage_1_id") REFERENCES "t_articles"("id") ON DELETE SET NULL;

ALTER TABLE "t_articles"       
  ADD COLUMN "report_stage" VARCHAR(128);