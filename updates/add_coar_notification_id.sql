ALTER table t_articles
ADD COLUMN if not exists coar_notification_id text;

ALTER table t_articles
ADD COLUMN if not exists coar_notification_closed boolean;

ALTER table t_coar_notification
ADD COLUMN if not exists coar_id text;
