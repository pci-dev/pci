-- all-sites updates to the database for version <n>
ALTER TABLE public.mail_queue ADD COLUMN  IF NOT EXISTS replyto_addresses character varying(1024);
