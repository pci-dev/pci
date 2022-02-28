ALTER TABLE "mail_queue"
ADD COLUMN  IF NOT EXISTS reminder_soon_due character varying(1024),
ADD COLUMN  IF NOT EXISTS reminder_due character varying(1024),
ADD COLUMN  IF NOT EXISTS reminder_over_due character varying(1024);
