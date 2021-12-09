alter table help_texts rename to help_text_old;
alter table help_texts_3 rename to help_texts;
alter sequence help_texts_id_seq owned by help_texts.id;

-- drop table help_text_old; -- => do that when deploying /next/ release
