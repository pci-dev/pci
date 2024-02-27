alter table config add column if not exists coar_whitelist text;
update config set coar_whitelist = '|127.0.0.1 LOCAL|';
