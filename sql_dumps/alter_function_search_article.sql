CREATE OR REPLACE FUNCTION public.search_articles(mythematics text[], mywords text[], mystatus character varying DEFAULT '''Recommended''::character varying', mylimit real DEFAULT '0.4', all_by_default boolean DEFAULT 'false')
   RETURNS TABLE (id integer, num integer, score double precision, title text, authors text, article_source character varying, doi character varying, abstract text, upload_timestamp timestamp without time zone, thematics character varying, keywords text, auto_nb_recommendations integer, status character varying, last_status_change timestamp without time zone, uploaded_picture character varying, already_published boolean, anonymous_submission boolean, parallel_submission boolean, art_stage_1_id integer)
  LANGUAGE plpgsql
  ROWS 1000
AS $function$
DECLARE
  myThematicsRegexp text;
BEGIN
  myThematicsRegexp := coalesce('('|| array_to_string(mythematics, ')|(') ||')', '^$');
  IF (mywords IS NOT NULL AND array_to_string(mywords,'') NOT LIKE '') THEN
	  PERFORM set_limit(mylimit);
	  RETURN QUERY WITH 
		q(w) AS (
			SELECT DISTINCT unaccent(unnest(mywords))
		),
		q0 AS (
			SELECT t_articles_words.article_id, max(similarity(word, w)*coef) AS max_sml
			FROM q
			JOIN t_distinct_words ON t_distinct_words.word % q.w
			JOIN t_articles_words ON t_distinct_words.id = t_articles_words.distinct_word_id
			GROUP BY t_articles_words.article_id, t_articles_words.distinct_word_id
		),
		qq AS (
			SELECT q0.article_id, round(sum(q0.max_sml)::numeric,2)::float8 AS score
			FROM q0
			GROUP BY q0.article_id
		)
		SELECT a.id, row_number() OVER (ORDER BY qq.score DESC, a.last_status_change DESC)::int, qq.score, 
			a.title, 
			CASE WHEN a.anonymous_submission THEN '[Undisclosed]'::varchar ELSE a.authors END AS authors, 
			a.article_source, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change, a.uploaded_picture, a.already_published,
			a.anonymous_submission, a.parallel_submission, a.art_stage_1_id
		  FROM t_articles AS a
		  JOIN qq ON a.id = qq.article_id
		  WHERE a.status LIKE myStatus
		  AND a.thematics ~* myThematicsRegexp
		  --AND qq.score > show_limit() * (SELECT count(w) FROM q)
		  ;
  ELSIF (all_by_default IS TRUE) THEN
		RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_status_change DESC)::int, NULL::float8, 
				a.title, 
				CASE WHEN a.anonymous_submission THEN '[Undisclosed]'::varchar ELSE a.authors END AS authors, 
				a.article_source, a.doi, a.abstract, a.upload_timestamp, 
				replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
				a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change, a.uploaded_picture, a.already_published,
				a.anonymous_submission, a.parallel_submission, a.art_stage_1_id
		FROM t_articles AS a
		WHERE a.status LIKE mystatus
		AND a.thematics ~* myThematicsRegexp;
  ELSE
	RETURN;
  END IF;
END;
$function$;
