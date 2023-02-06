ALTER TABLE "t_report_survey"
ADD COLUMN IF NOT EXISTS  tracked_changes_url character varying(512) DEFAULT '';
