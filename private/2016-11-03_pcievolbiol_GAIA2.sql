--
-- PostgreSQL database dump
--

-- Dumped from database version 9.1.23
-- Dumped by pg_dump version 9.3.15
-- Started on 2016-11-03 12:52:47 CET

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- TOC entry 253 (class 1255 OID 663452)
-- Name: alert_last_recommended_article_ids_for_user(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION alert_last_recommended_article_ids_for_user(userid integer) RETURNS integer[]
    LANGUAGE plpgsql
    AS $_$
DECLARE
  myThematicsRegexp text;
  myLastAlert timestamp without time zone;
  myIds int[];
BEGIN
  -- builds regexp based on user's thematics
  SELECT replace(regexp_replace(regexp_replace(u.thematics, E'^\\|', '('), E'\\|$', ')'), '|', ')|('), u.last_alert 
	FROM auth_user AS u 
	WHERE u.id=userId INTO myThematicsRegexp, myLastAlert;
  RAISE INFO 're=%', myThematicsRegexp;
  -- search articles recommended after last alert within user's thematics
  SELECT array_agg(a.id ORDER BY a.last_status_change DESC)
	FROM t_articles AS a
	WHERE a.status LIKE 'Recommended'
	AND a.last_status_change >= CASE WHEN myLastAlert IS NULL THEN statement_timestamp() - interval '8 days' ELSE myLastAlert END
	AND a.thematics ~* myThematicsRegexp
	INTO myIds;
  RETURN myIds;
END;
$_$;


--
-- TOC entry 251 (class 1255 OID 659879)
-- Name: auto_last_change_trigger_function(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION auto_last_change_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
      NEW.last_change = statement_timestamp();
      RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
      NEW.last_change = statement_timestamp();
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      RETURN OLD;
    END IF;
  END;
$$;


--
-- TOC entry 259 (class 1255 OID 662105)
-- Name: auto_last_status_change_trigger_function(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION auto_last_status_change_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
      NEW.last_status_change = statement_timestamp();
      RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
	IF (OLD.status != NEW.status) THEN
	    NEW.last_status_change = statement_timestamp();
	END IF;
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      RETURN OLD;
    END IF;
  END;
$$;


--
-- TOC entry 252 (class 1255 OID 659880)
-- Name: auto_nb_recommendations_trigger_function(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION auto_nb_recommendations_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
      PERFORM set_auto_nb_recommendations(NEW.article_id);
      RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
      PERFORM set_auto_nb_recommendations(OLD.article_id);
      PERFORM set_auto_nb_recommendations(NEW.article_id);
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      PERFORM set_auto_nb_recommendations(OLD.article_id);
      RETURN OLD;
    END IF;
  END;
$$;


--
-- TOC entry 256 (class 1255 OID 662072)
-- Name: distinct_words_trigger_function(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION distinct_words_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
		WITH w(article_id, coef, word) AS (
			SELECT DISTINCT a.id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(title, '')||E'\n'||coalesce(authors, '')||E'\n'||coalesce(keywords, '')||E'\n'))::text, ' '), '''', ''))
			FROM t_articles AS a WHERE a.id = NEW.id
			UNION
			SELECT DISTINCT a.id, 0.5, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(abstract, '')))::text, ' '), '''', ''))
			FROM t_articles AS a WHERE a.id = NEW.id
		)
		INSERT INTO t_articles_words (article_id, distinct_word_id, coef)
			SELECT article_id, get_distinct_word_id(word), max(coef)
			FROM w
			GROUP BY article_id, word;
		RETURN NEW;
	ELSIF (TG_OP = 'UPDATE') THEN
		DELETE FROM t_articles_words WHERE article_id = OLD.id;
		WITH w(article_id, coef, word) AS (
			SELECT DISTINCT a.id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(title, '')||E'\n'||coalesce(authors, '')||E'\n'||coalesce(keywords, '')||E'\n'))::text, ' '), '''', ''))
			FROM t_articles AS a WHERE a.id = NEW.id
			UNION
			SELECT DISTINCT a.id, 0.5, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(abstract, '')))::text, ' '), '''', ''))
			FROM t_articles AS a WHERE a.id = NEW.id
			UNION
			SELECT DISTINCT r.article_id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(recommendation_title, '')))::text, ' '), '''', ''))
			FROM t_recommendations AS r WHERE r.article_id = NEW.id AND r.recommendation_state LIKE 'Recommended'
			UNION
			SELECT DISTINCT r.article_id, 0.5, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(recommendation_comments, '')))::text, ' '), '''', ''))
			FROM t_recommendations AS r WHERE r.article_id = NEW.id AND r.recommendation_state LIKE 'Recommended'
			UNION
			SELECT DISTINCT r.article_id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(last_name, '')||' '||coalesce(first_name, '')))::text, ' '), '''', ''))
			FROM t_recommendations AS r 
			JOIN auth_user AS au ON r.recommender_id = au.id
			WHERE r.article_id = NEW.id AND r.recommendation_state LIKE 'Recommended'
			UNION
			SELECT DISTINCT r.article_id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
			coalesce(last_name, '')||' '||coalesce(first_name, '')))::text, ' '), '''', ''))
			FROM t_recommendations AS r 
			JOIN t_press_reviews AS pr ON pr.recommendation_id = r.id
			JOIN auth_user AS au ON contributor_id = au.id
			WHERE r.article_id = NEW.id AND r.recommendation_state LIKE 'Recommended'
		)
		INSERT INTO t_articles_words (article_id, distinct_word_id, coef)
			SELECT article_id, get_distinct_word_id(word), max(coef)
			FROM w
			GROUP BY article_id, word;
		RETURN NEW;
	ELSIF (TG_OP = 'DELETE') THEN
		--DELETE FROM t_articles_words WHERE article_id = OLD.id;
		RETURN OLD;
	END IF;
  END;
$$;


--
-- TOC entry 254 (class 1255 OID 662071)
-- Name: get_distinct_word_id(character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION get_distinct_word_id(myword character varying) RETURNS integer
    LANGUAGE plpgsql
    AS $$
DECLARE
  wid integer;
BEGIN 
  SELECT id FROM t_distinct_words WHERE word = myWord INTO wid;
  IF wid IS NULL THEN
    wid := nextval('t_distinct_words_id_seq'::regclass);
    INSERT INTO t_distinct_words (id, word) VALUES (wid, myWord);
  END IF;
  RETURN wid;
END;
$$;


--
-- TOC entry 258 (class 1255 OID 662222)
-- Name: propagate_field_deletion_function(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION propagate_field_deletion_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF (TG_OP = 'UPDATE') THEN
      UPDATE t_articles SET thematics = replace(thematics, '|'||OLD.keyword||'|', '|'||NEW.keyword||'|') WHERE thematics ~ OLD.keyword;
      UPDATE auth_user  SET thematics = replace(thematics, '|'||OLD.keyword||'|', '|'||NEW.keyword||'|') WHERE thematics ~ OLD.keyword;
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      UPDATE t_articles SET thematics = replace(thematics, '|'||OLD.keyword||'|', '|') WHERE thematics ~ OLD.keyword;
      UPDATE auth_user  SET thematics = replace(thematics, '|'||OLD.keyword||'|', '|') WHERE thematics ~ OLD.keyword;
      RETURN OLD;
    END IF;
END;
$$;


--
-- TOC entry 264 (class 1255 OID 663480)
-- Name: rewords_article(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION rewords_article(articleid integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
	DELETE FROM t_articles_words WHERE article_id = articleId;
	WITH w(article_id, coef, word) AS (
		SELECT DISTINCT a.id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(title, '')||E'\n'||coalesce(authors, '')||E'\n'||coalesce(keywords, '')||E'\n'))::text, ' '), '''', ''))
		FROM t_articles AS a WHERE a.id = articleId
		UNION
		SELECT DISTINCT a.id, 0.5, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(abstract, '')))::text, ' '), '''', ''))
		FROM t_articles AS a WHERE a.id = articleId
		UNION
		SELECT DISTINCT r.article_id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(recommendation_title, '')))::text, ' '), '''', ''))
		FROM t_recommendations AS r WHERE r.article_id = articleId AND r.recommendation_state LIKE 'Recommended'
		UNION
		SELECT DISTINCT r.article_id, 0.5, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(recommendation_comments, '')))::text, ' '), '''', ''))
		FROM t_recommendations AS r WHERE r.article_id = articleId AND r.recommendation_state LIKE 'Recommended'
		UNION
		SELECT DISTINCT r.article_id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(last_name, '')||' '||coalesce(first_name, '')))::text, ' '), '''', ''))
		FROM t_recommendations AS r 
		JOIN auth_user AS au ON r.recommender_id = au.id
		WHERE r.article_id = articleId AND r.recommendation_state LIKE 'Recommended'
		UNION
		SELECT DISTINCT r.article_id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(last_name, '')||' '||coalesce(first_name, '')))::text, ' '), '''', ''))
		FROM t_recommendations AS r 
		JOIN t_press_reviews AS pr ON pr.recommendation_id = r.id
		JOIN auth_user AS au ON contributor_id = au.id
		WHERE r.article_id = articleId AND r.recommendation_state LIKE 'Recommended'
	)
	INSERT INTO t_articles_words (article_id, distinct_word_id, coef)
		SELECT article_id, get_distinct_word_id(word), max(coef)
		FROM w
		GROUP BY article_id, word;
END;
$$;


--
-- TOC entry 265 (class 1255 OID 663952)
-- Name: search_articles(text[], text[], character varying, real, boolean); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION search_articles(mythematics text[], mywords text[], mystatus character varying DEFAULT 'Recommended'::character varying, mylimit real DEFAULT 0.4, all_by_default boolean DEFAULT false) RETURNS TABLE(id integer, num integer, score double precision, title text, authors text, article_source character varying, doi character varying, abstract text, upload_timestamp timestamp without time zone, thematics character varying, keywords text, auto_nb_recommendations integer, status character varying, last_status_change timestamp without time zone, uploaded_picture character varying)
    LANGUAGE plpgsql
    AS $_$
DECLARE
  myThematicsRegexp text;
BEGIN
  myThematicsRegexp := coalesce('('|| array_to_string(myThematics, ')|(') ||')', '^$');
  IF (myWords IS NOT NULL AND array_to_string(myWords,'') NOT LIKE '') THEN
	  PERFORM set_limit(myLimit);
	  RETURN QUERY WITH 
		q(w) AS (
			SELECT DISTINCT unaccent(unnest(myWords))
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
			a.title, a.authors, a.article_source, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change, a.uploaded_picture
		  FROM t_articles AS a
		  JOIN qq ON a.id = qq.article_id
		  WHERE a.status LIKE myStatus
		  AND a.thematics ~* myThematicsRegexp
		  --AND qq.score > show_limit() * (SELECT count(w) FROM q)
		  ;
  ELSIF (all_by_default IS TRUE) THEN
		RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_status_change DESC)::int, 1.0::float8, 
				a.title, a.authors, a.article_source, a.doi, a.abstract, a.upload_timestamp, 
				replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
				a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change, a.uploaded_picture
		FROM t_articles AS a
		WHERE a.status LIKE myStatus
		AND a.thematics ~* myThematicsRegexp;
  ELSE
	RETURN;
  END IF;
END;
$_$;


--
-- TOC entry 257 (class 1255 OID 662075)
-- Name: search_awaiting_articles(text[], text[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION search_awaiting_articles(mythematics text[], mywords text[]) RETURNS TABLE(id integer, num integer, score double precision, title text, authors text, doi character varying, abstract text, upload_timestamp timestamp without time zone, thematics character varying, keywords text, auto_nb_recommendations integer, status character varying, last_status_change timestamp without time zone)
    LANGUAGE plpgsql
    AS $_$
DECLARE
  myThematicsRegexp text;
BEGIN
  myThematicsRegexp := coalesce('('|| array_to_string(myThematics, ')|(') ||')', '^$');
  IF (myWords IS NOT NULL AND array_to_string(myWords,'') NOT LIKE '') THEN
	  RETURN QUERY WITH 
		q(w) AS (
			SELECT DISTINCT unaccent(unnest(myWords))
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
		SELECT a.id, row_number() OVER (ORDER BY qq.score DESC, a.upload_timestamp DESC)::int, qq.score, 
			a.title, a.authors, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change
		  FROM t_articles AS a
		  JOIN qq ON a.id = qq.article_id
		  WHERE a.status_id = 1
		  AND a.thematics ~* myThematicsRegexp
		  AND qq.score > show_limit() * array_length(myWords,1);
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.upload_timestamp DESC)::int, 1.0::float8, 
			a.title, a.authors, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change
	  FROM t_articles AS a
	  WHERE a.status LIKE 'Awaiting consideration'
	  AND a.thematics ~* myThematicsRegexp;
  END IF;
END;
$_$;


--
-- TOC entry 255 (class 1255 OID 662074)
-- Name: search_recommended_articles(text[], text[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION search_recommended_articles(mythematics text[], mywords text[]) RETURNS TABLE(id integer, num integer, score double precision, title text, authors text, doi character varying, abstract text, upload_timestamp timestamp without time zone, thematics character varying, keywords text, auto_nb_recommendations integer, status character varying, last_status_change timestamp without time zone)
    LANGUAGE plpgsql
    AS $_$
DECLARE
  myThematicsRegexp text;
BEGIN
  myThematicsRegexp := coalesce('('|| array_to_string(myThematics, ')|(') ||')', '^$');
  IF (myWords IS NOT NULL AND array_to_string(myWords,'') NOT LIKE '') THEN
	  RETURN QUERY WITH 
		q(w) AS (
			SELECT DISTINCT unaccent(unnest(myWords))
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
		SELECT a.id, row_number() OVER (ORDER BY qq.score DESC, a.upload_timestamp DESC)::int, qq.score, 
			a.title, a.authors, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change
		  FROM t_articles AS a
		  JOIN qq ON a.id = qq.article_id
		  WHERE a.status LIKE 'Recommended'
		  AND a.thematics ~* myThematicsRegexp
		  AND qq.score > show_limit() * array_length(myWords,1);
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.upload_timestamp DESC)::int, 1.0::float8, 
			a.title, a.authors, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change
	  FROM t_articles AS a
	  WHERE a.status LIKE 'Recommended'
	  AND a.thematics ~* myThematicsRegexp;
  END IF;
END;
$_$;


--
-- TOC entry 261 (class 1255 OID 662386)
-- Name: search_recommenders(text[], text[], integer[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION search_recommenders(mythematics text[], mywords text[], exclude integer[] DEFAULT ARRAY[]::integer[]) RETURNS TABLE(id integer, num integer, score double precision, first_name character varying, last_name character varying, email character varying, uploaded_picture character varying, city character varying, country character varying, laboratory character varying, institution character varying, thematics character varying)
    LANGUAGE plpgsql
    AS $_$
DECLARE
  myThematicsRegexp text;
BEGIN
  myThematicsRegexp := coalesce('('|| array_to_string(myThematics, ')|(') ||')', '^$');
  IF (myWords IS NOT NULL AND array_to_string(myWords,'') NOT LIKE '') THEN
	  RETURN QUERY WITH 
		q(w) AS (
			SELECT DISTINCT unaccent(unnest(myWords))
		),
		q0 AS (
			SELECT t_user_words.id AS user_id, word, similarity(word, w)*coef AS sml
			FROM t_user_words, q
			WHERE word % w
		),
		qq AS (
			SELECT q0.user_id, round(sum(q0.sml)::numeric,2)::float8 AS score
			FROM q0
			GROUP BY q0.user_id
		)
		SELECT a.id, row_number() OVER (ORDER BY qq.score DESC, a.last_name)::int, qq.score, 
			a.first_name, a.last_name, a.email, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics
		  FROM auth_user AS a
		  JOIN qq ON a.id = qq.user_id
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE g.role ILIKE 'recommender'
		  AND a.thematics ~* myThematicsRegexp
		  AND a.registration_key = ''
		  AND NOT a.id = ANY(exclude)
		  AND qq.score > show_limit() * (SELECT count(w) FROM q);
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_name)::int, 1.0::float8, 
			a.first_name, a.last_name, a.email, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics
		  FROM auth_user AS a
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE g.role ILIKE 'recommender'
		  AND a.registration_key = ''
		  AND NOT a.id = ANY(exclude)
		  AND a.thematics ~* myThematicsRegexp;
  END IF;
END;
$_$;


--
-- TOC entry 263 (class 1255 OID 663458)
-- Name: search_reviewers(text[], text[], integer[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION search_reviewers(mythematics text[], mywords text[], exclude integer[] DEFAULT ARRAY[]::integer[]) RETURNS TABLE(id integer, num integer, score double precision, first_name character varying, last_name character varying, email character varying, uploaded_picture character varying, city character varying, country character varying, laboratory character varying, institution character varying, thematics character varying, roles character varying)
    LANGUAGE plpgsql
    AS $_$
DECLARE
  myThematicsRegexp text;
BEGIN
  myThematicsRegexp := coalesce('('|| array_to_string(myThematics, ')|(') ||')', '^$');
  IF (myWords IS NOT NULL AND array_to_string(myWords,'') NOT LIKE '') THEN
	  RETURN QUERY WITH 
		q(w) AS (
			SELECT DISTINCT unaccent(unnest(myWords))
		),
		q0 AS (
			SELECT t_user_words.id AS user_id, word, similarity(word, w)*coef AS sml
			FROM t_user_words, q
			WHERE word % w
		),
		qq AS (
			SELECT q0.user_id, round(sum(q0.sml)::numeric,2)::float8 AS score
			FROM q0
			GROUP BY q0.user_id
		)
		SELECT a.id, row_number() OVER (ORDER BY qq.score DESC, a.last_name)::int, qq.score, 
			a.first_name, a.last_name, a.email, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			array_to_string(array_agg(g.role ORDER BY g.role), ', ')::varchar(1024)
		  FROM auth_user AS a
		  JOIN qq ON a.id = qq.user_id
		  LEFT JOIN auth_membership AS m ON a.id = m.user_id
		  LEFT JOIN auth_group AS g ON m.group_id = g.id
		  WHERE a.thematics ~* myThematicsRegexp
		  AND a.registration_key = ''
		  AND NOT a.id = ANY(exclude)
		  AND qq.score > show_limit() * (SELECT count(w) FROM q)
		  GROUP BY a.id, qq.score, a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution, a.thematics;
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_name)::int, 1.0::float8, 
			a.first_name, a.last_name, a.email, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			array_to_string(array_agg(g.role ORDER BY g.role), ', ')::varchar(1024)
		  FROM auth_user AS a
		  LEFT JOIN auth_membership AS m ON a.id = m.user_id
		  LEFT JOIN auth_group AS g ON m.group_id = g.id
		  WHERE a.thematics ~* myThematicsRegexp
		  AND a.registration_key = ''
		  AND NOT a.id = ANY(exclude)
		  GROUP BY a.id, a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution, a.thematics;
  END IF;
END;
$_$;


--
-- TOC entry 249 (class 1255 OID 659884)
-- Name: set_auto_keywords(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION set_auto_keywords(my_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
	WITH q(id, kws) AS (
		SELECT article_id, array_to_string(array_agg(keyword ORDER BY keyword), ', ')
		FROM t_keywords
		WHERE article_id = my_id
		GROUP BY article_id
	)
	UPDATE t_articles SET auto_keywords=kws 
	FROM q 
	WHERE t_articles.id=q.id;
END;
$$;


--
-- TOC entry 260 (class 1255 OID 662364)
-- Name: set_auto_nb_agreements(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION set_auto_nb_agreements(my_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  nb1 integer;
  nb2 integer;
BEGIN
  SELECT count(*) FROM t_press_reviews WHERE recommendation_id = my_id AND contribution_state LIKE 'Recommendation agreed' INTO nb1;
  SELECT count(*) FROM t_reviews       WHERE recommendation_id = my_id AND review_state       LIKE 'Terminated'            INTO nb2;
  UPDATE t_recommendations SET auto_nb_agreements=(nb1+nb2) WHERE id = my_id;
END;
$$;


--
-- TOC entry 250 (class 1255 OID 659885)
-- Name: set_auto_nb_recommendations(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION set_auto_nb_recommendations(my_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  nb integer;
BEGIN
  SELECT count(*) FROM t_recommendations WHERE article_id = my_id INTO nb;
  UPDATE t_articles SET auto_nb_recommendations = nb WHERE id = my_id;
END;
$$;


--
-- TOC entry 262 (class 1255 OID 659886)
-- Name: user_words_trigger_function(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION user_words_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
	WITH w(id, coef, word) AS (
	    SELECT DISTINCT a.id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(first_name, '')||E'\n'||coalesce(last_name, '')||E'\n'
		||coalesce(city, '')||E'\n'||coalesce(country, '')||E'\n'||coalesce(laboratory, '')||E'\n'
		||coalesce(institution, '')||E'\n'||coalesce(thematics, '')||E'\n'||coalesce(cv, '')||E'\n'))::text, ' '), '''', ''))
	    FROM auth_user AS a WHERE a.id = NEW.id
	)
	INSERT INTO t_user_words (id, coef, word)
	    SELECT id, max(coef), word
	    FROM w
	    GROUP BY id, word;
      RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        DELETE FROM t_user_words WHERE id = OLD.id;
	WITH w(id, coef, word) AS (
	    SELECT DISTINCT a.id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple', 
		coalesce(first_name, '')||E'\n'||coalesce(last_name, '')||E'\n'
		||coalesce(city, '')||E'\n'||coalesce(country, '')||E'\n'||coalesce(laboratory, '')||E'\n'
		||coalesce(institution, '')||E'\n'||coalesce(thematics, '')||E'\n'||coalesce(cv, '')||E'\n'))::text, ' '), '''', ''))
	    FROM auth_user AS a WHERE a.id = NEW.id
	)
	INSERT INTO t_user_words (id, coef, word)
	    SELECT id, max(coef), word
	    FROM w
	    GROUP BY id, word;
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        DELETE FROM t_user_words WHERE id = OLD.id;
        RETURN OLD;
    END IF;
  END;
$$;


SET default_with_oids = false;

--
-- TOC entry 165 (class 1259 OID 659888)
-- Name: auth_cas; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_cas (
    id integer NOT NULL,
    user_id integer,
    created_on timestamp without time zone,
    service character varying(512),
    ticket character varying(512),
    renew character(1)
);


--
-- TOC entry 166 (class 1259 OID 659894)
-- Name: auth_cas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_cas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2217 (class 0 OID 0)
-- Dependencies: 166
-- Name: auth_cas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_cas_id_seq OWNED BY auth_cas.id;


--
-- TOC entry 167 (class 1259 OID 659896)
-- Name: auth_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_event (
    id integer NOT NULL,
    time_stamp timestamp without time zone,
    client_ip character varying(512),
    user_id integer,
    origin character varying(512),
    description text
);


--
-- TOC entry 168 (class 1259 OID 659902)
-- Name: auth_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2218 (class 0 OID 0)
-- Dependencies: 168
-- Name: auth_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_event_id_seq OWNED BY auth_event.id;


--
-- TOC entry 169 (class 1259 OID 659904)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_group (
    id integer NOT NULL,
    role character varying(512),
    description text
);


--
-- TOC entry 170 (class 1259 OID 659910)
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2219 (class 0 OID 0)
-- Dependencies: 170
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_group_id_seq OWNED BY auth_group.id;


--
-- TOC entry 171 (class 1259 OID 659912)
-- Name: auth_membership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_membership (
    id integer NOT NULL,
    user_id integer,
    group_id integer
);


--
-- TOC entry 172 (class 1259 OID 659915)
-- Name: auth_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2220 (class 0 OID 0)
-- Dependencies: 172
-- Name: auth_membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_membership_id_seq OWNED BY auth_membership.id;


--
-- TOC entry 173 (class 1259 OID 659917)
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_permission (
    id integer NOT NULL,
    group_id integer,
    name character varying(512),
    table_name character varying(512),
    record_id integer
);


--
-- TOC entry 174 (class 1259 OID 659923)
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2221 (class 0 OID 0)
-- Dependencies: 174
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_permission_id_seq OWNED BY auth_permission.id;


--
-- TOC entry 175 (class 1259 OID 659925)
-- Name: auth_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE auth_user (
    id integer NOT NULL,
    first_name character varying(128),
    last_name character varying(128),
    email character varying(512),
    password character varying(512),
    registration_key character varying(512),
    reset_password_key character varying(512),
    registration_id character varying(512),
    picture_data bytea,
    uploaded_picture character varying(512),
    user_title character varying(10) DEFAULT ''::character varying,
    city character varying(512),
    country character varying(512),
    laboratory character varying(512),
    institution character varying(512),
    alerts character varying(512),
    thematics character varying(1024),
    cv text,
    last_alert timestamp without time zone
);


--
-- TOC entry 176 (class 1259 OID 659931)
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2222 (class 0 OID 0)
-- Dependencies: 176
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_user_id_seq OWNED BY auth_user.id;


--
-- TOC entry 177 (class 1259 OID 659933)
-- Name: old_statuses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE old_statuses (
    id integer NOT NULL,
    status character varying(50),
    color_class character varying(50)
);


--
-- TOC entry 203 (class 1259 OID 662184)
-- Name: scheduler_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scheduler_run (
    id integer NOT NULL,
    task_id integer,
    status character varying(512),
    start_time timestamp without time zone,
    stop_time timestamp without time zone,
    run_output text,
    run_result text,
    traceback text,
    worker_name character varying(512)
);


--
-- TOC entry 202 (class 1259 OID 662182)
-- Name: scheduler_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2223 (class 0 OID 0)
-- Dependencies: 202
-- Name: scheduler_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_run_id_seq OWNED BY scheduler_run.id;


--
-- TOC entry 201 (class 1259 OID 662171)
-- Name: scheduler_task; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scheduler_task (
    id integer NOT NULL,
    application_name character varying(512),
    task_name character varying(512),
    group_name character varying(512),
    status character varying(512),
    function_name character varying(512),
    uuid character varying(255),
    args text,
    vars text,
    enabled character(1),
    start_time timestamp without time zone,
    next_run_time timestamp without time zone,
    stop_time timestamp without time zone,
    repeats integer,
    retry_failed integer,
    period integer,
    prevent_drift character(1),
    timeout integer,
    sync_output integer,
    times_run integer,
    times_failed integer,
    last_run_time timestamp without time zone,
    assigned_worker_name character varying(512)
);


--
-- TOC entry 205 (class 1259 OID 662200)
-- Name: scheduler_task_deps; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scheduler_task_deps (
    id integer NOT NULL,
    job_name character varying(512),
    task_parent integer,
    task_child integer,
    can_visit character(1)
);


--
-- TOC entry 204 (class 1259 OID 662198)
-- Name: scheduler_task_deps_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_task_deps_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2224 (class 0 OID 0)
-- Dependencies: 204
-- Name: scheduler_task_deps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_task_deps_id_seq OWNED BY scheduler_task_deps.id;


--
-- TOC entry 200 (class 1259 OID 662169)
-- Name: scheduler_task_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_task_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2225 (class 0 OID 0)
-- Dependencies: 200
-- Name: scheduler_task_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_task_id_seq OWNED BY scheduler_task.id;


--
-- TOC entry 199 (class 1259 OID 662158)
-- Name: scheduler_worker; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE scheduler_worker (
    id integer NOT NULL,
    worker_name character varying(255),
    first_heartbeat timestamp without time zone,
    last_heartbeat timestamp without time zone,
    status character varying(512),
    is_ticker character(1),
    group_names text,
    worker_stats text
);


--
-- TOC entry 198 (class 1259 OID 662156)
-- Name: scheduler_worker_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_worker_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2226 (class 0 OID 0)
-- Dependencies: 198
-- Name: scheduler_worker_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_worker_id_seq OWNED BY scheduler_worker.id;


--
-- TOC entry 178 (class 1259 OID 659936)
-- Name: t_articles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_articles (
    id integer NOT NULL,
    title text,
    doi character varying(512),
    abstract text,
    upload_timestamp timestamp without time zone DEFAULT statement_timestamp(),
    user_id integer,
    authors text,
    thematics character varying(1024),
    keywords text,
    auto_nb_recommendations integer DEFAULT 0,
    suggested_recommender_id integer,
    status character varying(50) NOT NULL,
    last_status_change timestamp without time zone DEFAULT statement_timestamp(),
    article_source character varying(1024),
    is_not_reviewed_elsewhere boolean,
    already_published boolean DEFAULT false,
    i_am_an_author boolean,
    picture_data bytea,
    uploaded_picture character varying(512),
    picture_rights_ok boolean DEFAULT false
);


--
-- TOC entry 179 (class 1259 OID 659945)
-- Name: t_articles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_articles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2227 (class 0 OID 0)
-- Dependencies: 179
-- Name: t_articles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_articles_id_seq OWNED BY t_articles.id;


--
-- TOC entry 194 (class 1259 OID 662054)
-- Name: t_articles_words; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_articles_words (
    article_id integer NOT NULL,
    distinct_word_id integer NOT NULL,
    coef real DEFAULT 1.0
);


--
-- TOC entry 214 (class 1259 OID 664152)
-- Name: t_comments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_comments (
    id integer NOT NULL,
    article_id integer,
    parent_id integer,
    user_id integer,
    user_comment text,
    comment_datetime timestamp without time zone DEFAULT statement_timestamp()
);


--
-- TOC entry 213 (class 1259 OID 664150)
-- Name: t_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2228 (class 0 OID 0)
-- Dependencies: 213
-- Name: t_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_comments_id_seq OWNED BY t_comments.id;


--
-- TOC entry 192 (class 1259 OID 662043)
-- Name: t_distinct_words_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_distinct_words_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 193 (class 1259 OID 662045)
-- Name: t_distinct_words; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_distinct_words (
    id integer DEFAULT nextval('t_distinct_words_id_seq'::regclass) NOT NULL,
    word character varying(250)
);


--
-- TOC entry 180 (class 1259 OID 659947)
-- Name: t_thematics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_thematics (
    id integer NOT NULL,
    keyword character varying(512)
);


--
-- TOC entry 181 (class 1259 OID 659953)
-- Name: t_keywords_list_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_keywords_list_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2229 (class 0 OID 0)
-- Dependencies: 181
-- Name: t_keywords_list_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_keywords_list_id_seq OWNED BY t_thematics.id;


--
-- TOC entry 208 (class 1259 OID 662313)
-- Name: t_press_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_press_reviews (
    id integer NOT NULL,
    recommendation_id integer,
    contributor_id integer
);


--
-- TOC entry 207 (class 1259 OID 662311)
-- Name: t_press_review_contributors_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_press_review_contributors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2230 (class 0 OID 0)
-- Dependencies: 207
-- Name: t_press_review_contributors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_press_review_contributors_id_seq OWNED BY t_press_reviews.id;


--
-- TOC entry 182 (class 1259 OID 659955)
-- Name: t_recommendations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_recommendations (
    id integer NOT NULL,
    article_id integer,
    recommendation_comments text,
    recommendation_timestamp timestamp without time zone DEFAULT statement_timestamp(),
    doi character varying(512),
    recommender_id integer,
    last_change timestamp without time zone DEFAULT statement_timestamp(),
    reply text,
    is_closed boolean DEFAULT false,
    is_press_review boolean DEFAULT false,
    auto_nb_agreements integer DEFAULT 0,
    no_conflict_of_interest boolean,
    recommendation_title character varying(1024),
    recommendation_doi character varying(512),
    recommendation_state character varying(50)
);


--
-- TOC entry 183 (class 1259 OID 659963)
-- Name: t_recommendations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_recommendations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2231 (class 0 OID 0)
-- Dependencies: 183
-- Name: t_recommendations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_recommendations_id_seq OWNED BY t_recommendations.id;


--
-- TOC entry 184 (class 1259 OID 659965)
-- Name: t_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_reviews (
    id integer NOT NULL,
    recommendation_id integer,
    reviewer_id integer,
    review text,
    last_change timestamp without time zone DEFAULT statement_timestamp(),
    is_closed boolean DEFAULT false,
    anonymously boolean DEFAULT false,
    review_state character varying(50) DEFAULT 'Pending'::character varying NOT NULL,
    no_conflict_of_interest boolean
);


--
-- TOC entry 185 (class 1259 OID 659968)
-- Name: t_reviewers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_reviewers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2232 (class 0 OID 0)
-- Dependencies: 185
-- Name: t_reviewers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_reviewers_id_seq OWNED BY t_reviews.id;


--
-- TOC entry 186 (class 1259 OID 659970)
-- Name: t_status_article; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_status_article (
    id integer NOT NULL,
    status character varying(50),
    color_class character varying(50),
    explaination text,
    priority_level character(1)
);


--
-- TOC entry 187 (class 1259 OID 659976)
-- Name: t_status_article_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_status_article_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2233 (class 0 OID 0)
-- Dependencies: 187
-- Name: t_status_article_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_status_article_id_seq OWNED BY t_status_article.id;


--
-- TOC entry 196 (class 1259 OID 662084)
-- Name: t_suggested_recommenders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_suggested_recommenders (
    id integer NOT NULL,
    article_id integer,
    suggested_recommender_id integer,
    email_sent boolean DEFAULT false
);


--
-- TOC entry 195 (class 1259 OID 662082)
-- Name: t_suggested_recommenders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_suggested_recommenders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2234 (class 0 OID 0)
-- Dependencies: 195
-- Name: t_suggested_recommenders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_suggested_recommenders_id_seq OWNED BY t_suggested_recommenders.id;


--
-- TOC entry 188 (class 1259 OID 659986)
-- Name: t_user_words; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE t_user_words (
    id integer,
    word character varying(250),
    coef real DEFAULT 1.0
);


--
-- TOC entry 210 (class 1259 OID 662340)
-- Name: v_article_recommender; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_article_recommender AS
SELECT a.id, array_to_string(array_agg(DISTINCT (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text)), ', '::text) AS recommender FROM ((t_articles a LEFT JOIN t_recommendations r ON (((a.id = r.article_id) AND (r.is_closed IS FALSE)))) LEFT JOIN auth_user au ON ((r.recommender_id = au.id))) GROUP BY a.id;


--
-- TOC entry 191 (class 1259 OID 662028)
-- Name: v_last_recommendation; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_last_recommendation AS
SELECT DISTINCT u.id, max(r.last_change) AS last_recommendation, ((statement_timestamp())::date - (max(r.last_change))::date) AS days_since_last_recommendation FROM (auth_user u LEFT JOIN t_recommendations r ON ((u.id = r.recommender_id))) GROUP BY u.id;


--
-- TOC entry 211 (class 1259 OID 662345)
-- Name: v_recommendation_contributors; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_recommendation_contributors AS
SELECT r.id, array_to_string(array_agg(DISTINCT (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text)), ', '::text) AS contributors FROM ((t_recommendations r LEFT JOIN t_press_reviews c ON ((c.recommendation_id = r.id))) LEFT JOIN auth_user au ON ((c.contributor_id = au.id))) GROUP BY r.id;


--
-- TOC entry 197 (class 1259 OID 662118)
-- Name: v_reviewers; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_reviewers AS
SELECT r.id, array_to_string(array_agg(CASE WHEN ((au.id IS NOT NULL) AND ((rv.anonymously IS FALSE) OR (rv.anonymously IS NULL))) THEN ((COALESCE(((au.user_title)::text || ' '::text), ''::text) || COALESCE(((au.first_name)::text || ' '::text), ''::text)) || (COALESCE(au.last_name, ''::character varying))::text) WHEN (rv.anonymously IS TRUE) THEN 'Anonymous'::text ELSE ''::text END), ', '::text) AS reviewers FROM ((t_recommendations r LEFT JOIN t_reviews rv ON ((r.id = rv.recommendation_id))) LEFT JOIN auth_user au ON ((rv.reviewer_id = au.id))) GROUP BY r.id;


--
-- TOC entry 212 (class 1259 OID 662350)
-- Name: v_reviewers_named; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_reviewers_named AS
SELECT r.id, array_to_string(array_agg(CASE WHEN ((rv.id IS NOT NULL) AND (au.id IS NOT NULL)) THEN (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text) WHEN ((rv.id IS NOT NULL) AND (au.id IS NULL)) THEN '[Unnamed]'::text ELSE ''::text END), ', '::text) AS reviewers FROM ((t_recommendations r LEFT JOIN t_reviews rv ON ((r.id = rv.recommendation_id))) LEFT JOIN auth_user au ON ((rv.reviewer_id = au.id))) GROUP BY r.id;


--
-- TOC entry 206 (class 1259 OID 662217)
-- Name: v_roles; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_roles AS
SELECT auth_user.id, (array_to_string(array_agg(auth_group.role), ', '::text))::character varying(512) AS roles FROM ((auth_user LEFT JOIN auth_membership ON ((auth_membership.user_id = auth_user.id))) LEFT JOIN auth_group ON ((auth_group.id = auth_membership.group_id))) GROUP BY auth_user.id;


--
-- TOC entry 209 (class 1259 OID 662335)
-- Name: v_suggested_recommenders; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_suggested_recommenders AS
SELECT a.id, array_to_string(array_agg(DISTINCT (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text)), ', '::text) AS suggested_recommenders FROM ((t_articles a LEFT JOIN t_suggested_recommenders sr ON ((a.id = sr.article_id))) LEFT JOIN auth_user au ON ((sr.suggested_recommender_id = au.id))) GROUP BY a.id;


--
-- TOC entry 1974 (class 2604 OID 660002)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_cas ALTER COLUMN id SET DEFAULT nextval('auth_cas_id_seq'::regclass);


--
-- TOC entry 1975 (class 2604 OID 660003)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_event ALTER COLUMN id SET DEFAULT nextval('auth_event_id_seq'::regclass);


--
-- TOC entry 1976 (class 2604 OID 660004)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group ALTER COLUMN id SET DEFAULT nextval('auth_group_id_seq'::regclass);


--
-- TOC entry 1977 (class 2604 OID 660005)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_membership ALTER COLUMN id SET DEFAULT nextval('auth_membership_id_seq'::regclass);


--
-- TOC entry 1978 (class 2604 OID 660006)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission ALTER COLUMN id SET DEFAULT nextval('auth_permission_id_seq'::regclass);


--
-- TOC entry 1979 (class 2604 OID 660007)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_user ALTER COLUMN id SET DEFAULT nextval('auth_user_id_seq'::regclass);


--
-- TOC entry 2007 (class 2604 OID 662187)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_run ALTER COLUMN id SET DEFAULT nextval('scheduler_run_id_seq'::regclass);


--
-- TOC entry 2006 (class 2604 OID 662174)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task ALTER COLUMN id SET DEFAULT nextval('scheduler_task_id_seq'::regclass);


--
-- TOC entry 2008 (class 2604 OID 662203)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task_deps ALTER COLUMN id SET DEFAULT nextval('scheduler_task_deps_id_seq'::regclass);


--
-- TOC entry 2005 (class 2604 OID 662161)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_worker ALTER COLUMN id SET DEFAULT nextval('scheduler_worker_id_seq'::regclass);


--
-- TOC entry 1984 (class 2604 OID 660008)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles ALTER COLUMN id SET DEFAULT nextval('t_articles_id_seq'::regclass);


--
-- TOC entry 2010 (class 2604 OID 664155)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_comments ALTER COLUMN id SET DEFAULT nextval('t_comments_id_seq'::regclass);


--
-- TOC entry 2009 (class 2604 OID 662316)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_press_reviews ALTER COLUMN id SET DEFAULT nextval('t_press_review_contributors_id_seq'::regclass);


--
-- TOC entry 1990 (class 2604 OID 660009)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_recommendations ALTER COLUMN id SET DEFAULT nextval('t_recommendations_id_seq'::regclass);


--
-- TOC entry 1994 (class 2604 OID 660010)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews ALTER COLUMN id SET DEFAULT nextval('t_reviewers_id_seq'::regclass);


--
-- TOC entry 1999 (class 2604 OID 660011)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_status_article ALTER COLUMN id SET DEFAULT nextval('t_status_article_id_seq'::regclass);


--
-- TOC entry 2003 (class 2604 OID 662087)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders ALTER COLUMN id SET DEFAULT nextval('t_suggested_recommenders_id_seq'::regclass);


--
-- TOC entry 1987 (class 2604 OID 660013)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_thematics ALTER COLUMN id SET DEFAULT nextval('t_keywords_list_id_seq'::regclass);


--
-- TOC entry 2013 (class 2606 OID 661893)
-- Name: auth_cas_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_cas
    ADD CONSTRAINT auth_cas_pkey PRIMARY KEY (id);


--
-- TOC entry 2015 (class 2606 OID 661895)
-- Name: auth_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_event
    ADD CONSTRAINT auth_event_pkey PRIMARY KEY (id);


--
-- TOC entry 2017 (class 2606 OID 661897)
-- Name: auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 2019 (class 2606 OID 661899)
-- Name: auth_membership_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_membership
    ADD CONSTRAINT auth_membership_pkey PRIMARY KEY (id);


--
-- TOC entry 2021 (class 2606 OID 661901)
-- Name: auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 2023 (class 2606 OID 661903)
-- Name: auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- TOC entry 2064 (class 2606 OID 662192)
-- Name: scheduler_run_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_run
    ADD CONSTRAINT scheduler_run_pkey PRIMARY KEY (id);


--
-- TOC entry 2066 (class 2606 OID 662208)
-- Name: scheduler_task_deps_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task_deps
    ADD CONSTRAINT scheduler_task_deps_pkey PRIMARY KEY (id);


--
-- TOC entry 2060 (class 2606 OID 662179)
-- Name: scheduler_task_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task
    ADD CONSTRAINT scheduler_task_pkey PRIMARY KEY (id);


--
-- TOC entry 2062 (class 2606 OID 662181)
-- Name: scheduler_task_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task
    ADD CONSTRAINT scheduler_task_uuid_key UNIQUE (uuid);


--
-- TOC entry 2056 (class 2606 OID 662166)
-- Name: scheduler_worker_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_worker
    ADD CONSTRAINT scheduler_worker_pkey PRIMARY KEY (id);


--
-- TOC entry 2058 (class 2606 OID 662168)
-- Name: scheduler_worker_worker_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_worker
    ADD CONSTRAINT scheduler_worker_worker_name_key UNIQUE (worker_name);


--
-- TOC entry 2028 (class 2606 OID 661905)
-- Name: t_articles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT t_articles_pkey PRIMARY KEY (id);


--
-- TOC entry 2072 (class 2606 OID 664161)
-- Name: t_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_comments
    ADD CONSTRAINT t_comments_pkey PRIMARY KEY (id);


--
-- TOC entry 2044 (class 2606 OID 662050)
-- Name: t_distinct_words_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_distinct_words
    ADD CONSTRAINT t_distinct_words_pkey PRIMARY KEY (id);


--
-- TOC entry 2047 (class 2606 OID 662053)
-- Name: t_distinct_words_word_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_distinct_words
    ADD CONSTRAINT t_distinct_words_word_unique UNIQUE (word);


--
-- TOC entry 2030 (class 2606 OID 661907)
-- Name: t_keywords_list_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_thematics
    ADD CONSTRAINT t_keywords_list_pkey PRIMARY KEY (id);


--
-- TOC entry 2068 (class 2606 OID 662319)
-- Name: t_press_review_contributors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_press_reviews
    ADD CONSTRAINT t_press_review_contributors_pkey PRIMARY KEY (id);


--
-- TOC entry 2032 (class 2606 OID 661909)
-- Name: t_recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_recommendations
    ADD CONSTRAINT t_recommendations_pkey PRIMARY KEY (id);


--
-- TOC entry 2035 (class 2606 OID 661911)
-- Name: t_reviewers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews
    ADD CONSTRAINT t_reviewers_pkey PRIMARY KEY (id);


--
-- TOC entry 2039 (class 2606 OID 661913)
-- Name: t_status_article_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_status_article
    ADD CONSTRAINT t_status_article_pkey PRIMARY KEY (id);


--
-- TOC entry 2041 (class 2606 OID 661915)
-- Name: t_status_article_status_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_status_article
    ADD CONSTRAINT t_status_article_status_key UNIQUE (status);


--
-- TOC entry 2025 (class 2606 OID 661921)
-- Name: t_statuses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY old_statuses
    ADD CONSTRAINT t_statuses_pkey PRIMARY KEY (id);


--
-- TOC entry 2052 (class 2606 OID 662089)
-- Name: t_suggested_recommenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT t_suggested_recommenders_pkey PRIMARY KEY (id);


--
-- TOC entry 2050 (class 2606 OID 662059)
-- Name: tarticleswords_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles_words
    ADD CONSTRAINT tarticleswords_pkey PRIMARY KEY (distinct_word_id, article_id);


--
-- TOC entry 2070 (class 2606 OID 662370)
-- Name: tpressreviewcontribs_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_press_reviews
    ADD CONSTRAINT tpressreviewcontribs_unique UNIQUE (recommendation_id, contributor_id);


--
-- TOC entry 2037 (class 2606 OID 662368)
-- Name: treviews_recomm_reviewer_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews
    ADD CONSTRAINT treviews_recomm_reviewer_unique UNIQUE (recommendation_id, reviewer_id);


--
-- TOC entry 2054 (class 2606 OID 662110)
-- Name: tsuggestedrecommenders_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_unique UNIQUE (article_id, suggested_recommender_id);


--
-- TOC entry 2026 (class 1259 OID 663478)
-- Name: t_articles_last_status_change_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX t_articles_last_status_change_idx ON t_articles USING btree (last_status_change DESC NULLS LAST);


--
-- TOC entry 2045 (class 1259 OID 662051)
-- Name: t_distinct_words_word_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX t_distinct_words_word_idx ON t_distinct_words USING btree (word);


--
-- TOC entry 2048 (class 1259 OID 663479)
-- Name: tdistinctwords_gist; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tdistinctwords_gist ON t_distinct_words USING gist (word gist_trgm_ops);


--
-- TOC entry 2033 (class 1259 OID 662131)
-- Name: trecommendations_articleid_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX trecommendations_articleid_idx ON t_recommendations USING btree (article_id);


--
-- TOC entry 2042 (class 1259 OID 661924)
-- Name: tuserwords_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX tuserwords_idx ON t_user_words USING gist (word gist_trgm_ops);


--
-- TOC entry 2102 (class 2620 OID 662107)
-- Name: auto_last_change_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_last_change_trigger BEFORE INSERT OR DELETE OR UPDATE ON t_recommendations FOR EACH ROW EXECUTE PROCEDURE auto_last_change_trigger_function();


--
-- TOC entry 2103 (class 2620 OID 662108)
-- Name: auto_last_change_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_last_change_trigger BEFORE INSERT OR DELETE OR UPDATE ON t_reviews FOR EACH ROW EXECUTE PROCEDURE auto_last_change_trigger_function();


--
-- TOC entry 2098 (class 2620 OID 663476)
-- Name: auto_last_status_change_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_last_status_change_trigger BEFORE INSERT OR UPDATE OF status ON t_articles FOR EACH ROW EXECUTE PROCEDURE auto_last_status_change_trigger_function();


--
-- TOC entry 2101 (class 2620 OID 661938)
-- Name: auto_nb_recommendations_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_nb_recommendations_trigger AFTER INSERT OR DELETE OR UPDATE ON t_recommendations FOR EACH ROW EXECUTE PROCEDURE auto_nb_recommendations_trigger_function();


--
-- TOC entry 2099 (class 2620 OID 663477)
-- Name: distinct_words_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER distinct_words_trigger AFTER INSERT OR UPDATE OF title, abstract, keywords, authors ON t_articles FOR EACH ROW EXECUTE PROCEDURE distinct_words_trigger_function();


--
-- TOC entry 2100 (class 2620 OID 662223)
-- Name: propagate_field_deletion_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER propagate_field_deletion_trigger AFTER DELETE OR UPDATE OF keyword ON t_thematics FOR EACH ROW EXECUTE PROCEDURE propagate_field_deletion_function();


--
-- TOC entry 2097 (class 2620 OID 661939)
-- Name: user_words_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER user_words_trigger AFTER INSERT OR DELETE OR UPDATE OF first_name, last_name, city, country, laboratory, institution, thematics ON auth_user FOR EACH ROW EXECUTE PROCEDURE user_words_trigger_function();


--
-- TOC entry 2073 (class 2606 OID 661941)
-- Name: auth_cas_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_cas
    ADD CONSTRAINT auth_cas_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;


--
-- TOC entry 2074 (class 2606 OID 661946)
-- Name: auth_event_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_event
    ADD CONSTRAINT auth_event_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;


--
-- TOC entry 2075 (class 2606 OID 661951)
-- Name: auth_membership_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_membership
    ADD CONSTRAINT auth_membership_group_id_fkey FOREIGN KEY (group_id) REFERENCES auth_group(id) ON DELETE CASCADE;


--
-- TOC entry 2076 (class 2606 OID 661956)
-- Name: auth_membership_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_membership
    ADD CONSTRAINT auth_membership_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;


--
-- TOC entry 2077 (class 2606 OID 661961)
-- Name: auth_permission_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_group_id_fkey FOREIGN KEY (group_id) REFERENCES auth_group(id) ON DELETE CASCADE;


--
-- TOC entry 2090 (class 2606 OID 662193)
-- Name: scheduler_run_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_run
    ADD CONSTRAINT scheduler_run_task_id_fkey FOREIGN KEY (task_id) REFERENCES scheduler_task(id) ON DELETE CASCADE;


--
-- TOC entry 2091 (class 2606 OID 662209)
-- Name: scheduler_task_deps_task_child_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task_deps
    ADD CONSTRAINT scheduler_task_deps_task_child_fkey FOREIGN KEY (task_child) REFERENCES scheduler_task(id) ON DELETE CASCADE;


--
-- TOC entry 2078 (class 2606 OID 661966)
-- Name: t_articles_suggested_recommender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT t_articles_suggested_recommender_id_fkey FOREIGN KEY (suggested_recommender_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2079 (class 2606 OID 661971)
-- Name: t_articles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT t_articles_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2095 (class 2606 OID 664167)
-- Name: t_comments_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_comments
    ADD CONSTRAINT t_comments_article_id_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2096 (class 2606 OID 664172)
-- Name: t_comments_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_comments
    ADD CONSTRAINT t_comments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES t_comments(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2094 (class 2606 OID 664162)
-- Name: t_comments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_comments
    ADD CONSTRAINT t_comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 2093 (class 2606 OID 662325)
-- Name: t_press_review_contributors_contributor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_press_reviews
    ADD CONSTRAINT t_press_review_contributors_contributor_id_fkey FOREIGN KEY (contributor_id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 2082 (class 2606 OID 662038)
-- Name: t_recommendations_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_recommendations
    ADD CONSTRAINT t_recommendations_article_id_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON DELETE CASCADE;


--
-- TOC entry 2081 (class 2606 OID 661981)
-- Name: t_recommendations_recommender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_recommendations
    ADD CONSTRAINT t_recommendations_recommender_id_fkey FOREIGN KEY (recommender_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2083 (class 2606 OID 661986)
-- Name: t_reviewers_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews
    ADD CONSTRAINT t_reviewers_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES t_recommendations(id) ON DELETE CASCADE;


--
-- TOC entry 2084 (class 2606 OID 661991)
-- Name: t_reviewers_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews
    ADD CONSTRAINT t_reviewers_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2080 (class 2606 OID 661996)
-- Name: tarticles_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT tarticles_status_fkey FOREIGN KEY (status) REFERENCES t_status_article(status);


--
-- TOC entry 2086 (class 2606 OID 662060)
-- Name: tarticleswords_tarticles_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles_words
    ADD CONSTRAINT tarticleswords_tarticles_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2087 (class 2606 OID 662065)
-- Name: tarticleswords_tdistinctwords_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles_words
    ADD CONSTRAINT tarticleswords_tdistinctwords_fkey FOREIGN KEY (distinct_word_id) REFERENCES t_distinct_words(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2092 (class 2606 OID 662320)
-- Name: tpressreview_trecommendation_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_press_reviews
    ADD CONSTRAINT tpressreview_trecommendation_fkey FOREIGN KEY (recommendation_id) REFERENCES t_recommendations(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2089 (class 2606 OID 662095)
-- Name: tsuggestedrecommenders_authusers_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_authusers_fkey FOREIGN KEY (suggested_recommender_id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2088 (class 2606 OID 662090)
-- Name: tsuggestedrecommenders_tarticles_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_tarticles_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2085 (class 2606 OID 662006)
-- Name: tuserwords_authuser_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_user_words
    ADD CONSTRAINT tuserwords_authuser_fkey FOREIGN KEY (id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE;


-- Completed on 2016-11-03 12:52:48 CET

--
-- PostgreSQL database dump complete
--

