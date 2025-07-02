alter table t_articles add column if not exists show_all_doi bool default true;
update t_articles set show_all_doi = false;
