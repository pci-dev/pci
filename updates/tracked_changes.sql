ALTER TABLE "t_report_survey"
ADD COLUMN IF NOT EXISTS  tracked_changes_url character varying(512) DEFAULT '';

ALTER TABLE "t_report_survey" 
RENAME COLUMN "q30" TO "q30_details";

ALTER TABLE "t_report_survey"
ADD COLUMN IF NOT EXISTS  q30 character varying(512) DEFAULT '';
