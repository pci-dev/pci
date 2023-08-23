ALTER TABLE "mail_queue" 
ADD COLUMN IF NOT EXISTS sender_name varchar(256);
