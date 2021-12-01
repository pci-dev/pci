-- all-sites updates to the database for version <n>

ALTER TABLE public.mail_queue ADD COLUMN  IF NOT EXISTS replyto_addresses character varying(1024);

ALTER TABLE public.t_report_survey ADD COLUMN  IF NOT EXISTS q1_1 character varying(1024);
ALTER TABLE public.t_report_survey ADD COLUMN  IF NOT EXISTS q1_2 character varying(256);

ALTER TABLE public.t_report_survey ADD COLUMN  IF NOT EXISTS q32 boolean;
