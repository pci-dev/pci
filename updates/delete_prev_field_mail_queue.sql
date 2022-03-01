ALTER TABLE "mail_queue"
DROP COLUMN  IF EXISTS reminder_soon_due,
DROP COLUMN  IF EXISTS reminder_due,
DROP COLUMN  IF EXISTS reminder_over_due;
