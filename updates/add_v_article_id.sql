CREATE VIEW v_article_id AS
 SELECT
	id,
	concat('#', id) as id_str
 FROM t_articles;
