ALTER TABLE "public"."t_articles"
  ADD COLUMN "art_stage_1_id" integer,
  ADD FOREIGN KEY ("art_stage_1_id") REFERENCES "public"."t_articles"("id") ON DELETE SET NULL;
  
ALTER TABLE "t_articles" ADD COLUMN "scheduled_submission_date" date;