ALTER TABLE "t_report_survey"
ADD COLUMN IF NOT EXISTS  report_server character varying(512) DEFAULT '';
