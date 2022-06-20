UPDATE  "t_articles"
SET  data_doi = '||' WHERE data_doi IS NULL;

UPDATE  "t_articles"
SET  scripts_doi = '||' WHERE scripts_doi IS NULL;

UPDATE  "t_articles"
SET  codes_doi = '||' WHERE codes_doi IS NULL;
