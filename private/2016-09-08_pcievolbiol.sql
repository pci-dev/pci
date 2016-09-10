--
-- PostgreSQL database dump
--

-- Dumped from database version 9.3.14
-- Dumped by pg_dump version 9.3.14
-- Started on 2016-09-08 15:10:16 CEST

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

SET search_path = public, pg_catalog;

--
-- TOC entry 255 (class 1255 OID 87782634)
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
-- TOC entry 259 (class 1255 OID 87785079)
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
      NEW.last_status_change = statement_timestamp();
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      RETURN OLD;
    END IF;
  END;
$$;


--
-- TOC entry 251 (class 1255 OID 87778825)
-- Name: auto_nb_recommendations_trigger_function(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION auto_nb_recommendations_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
      PERFORM set_auto_nb_recommendations(NEW.article_id);
      UPDATE t_articles SET status = 'Under consideration' WHERE id = NEW.article_id AND status LIKE 'Awaiting consideration';
      RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
      PERFORM set_auto_nb_recommendations(OLD.article_id);
      PERFORM set_auto_nb_recommendations(NEW.article_id);
      UPDATE t_articles SET status = 'Awaiting consideration' WHERE id = OLD.article_id AND status LIKE 'Under consideration';
      UPDATE t_articles SET status = 'Under consideration' WHERE id = NEW.article_id AND status LIKE 'Awaiting consideration';
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      PERFORM set_auto_nb_recommendations(OLD.article_id);
      UPDATE t_articles SET status = 'Awaiting consideration' WHERE id = OLD.article_id AND status LIKE 'Under consideration';
      RETURN OLD;
    END IF;
  END;
$$;


--
-- TOC entry 256 (class 1255 OID 87784973)
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
		)
		INSERT INTO t_articles_words (article_id, distinct_word_id, coef)
			SELECT article_id, get_distinct_word_id(word), max(coef)
			FROM w
			GROUP BY article_id, word;
		RETURN NEW;
	ELSIF (TG_OP = 'DELETE') THEN
		DELETE FROM t_articles_words WHERE article_id = OLD.id;
		RETURN OLD;
	END IF;
  END;
$$;


--
-- TOC entry 254 (class 1255 OID 87784972)
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
-- TOC entry 257 (class 1255 OID 87785076)
-- Name: search_articles(text[], text[], character varying, real); Type: FUNCTION; Schema: public; Owner: -
--

DROP FUNCTION IF EXISTS search_articles(text[], text[], varchar(50), real);
CREATE OR REPLACE FUNCTION search_articles(myThematics text[], myWords text[], myStatus varchar(50) DEFAULT 'Recommended', myLimit real DEFAULT 0.4)
  RETURNS TABLE (
	id integer,
	num integer,
	score float8,
	title text,
	authors text,
	doi varchar(512),
	abstract text,
	upload_timestamp timestamp without time zone,
	thematics character varying(1024),
	keywords text,
	auto_nb_recommendations integer,
	status varchar(50),
	last_status_change timestamp without time zone
  ) AS 
$BODY$
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
			a.title, a.authors, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change
		  FROM t_articles AS a
		  JOIN qq ON a.id = qq.article_id
		  WHERE a.status LIKE myStatus
		  AND a.thematics ~* myThematicsRegexp
		  AND qq.score > show_limit() * (SELECT count(w) FROM q);
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_status_change DESC)::int, 1.0::float8, 
			a.title, a.authors, a.doi, a.abstract, a.upload_timestamp, 
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.keywords, a.auto_nb_recommendations, a.status, a.last_status_change
	  FROM t_articles AS a
	  WHERE a.status LIKE myStatus
	  AND a.thematics ~* myThematicsRegexp;
  END IF;
END;
$BODY$
LANGUAGE plpgsql VOLATILE;


--
-- TOC entry 258 (class 1255 OID 87785077)
-- Name: search_recommenders(text[], text[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION search_recommenders(mythematics text[], mywords text[]) RETURNS TABLE(id integer, num integer, score double precision, user_title character varying, first_name character varying, last_name character varying, uploaded_picture character varying, city character varying, country character varying, laboratory character varying, institution character varying, thematics character varying)
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
			a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics
		  FROM auth_user AS a
		  JOIN qq ON a.id = qq.user_id
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE g.role ILIKE 'recommender'
		  AND a.thematics ~* myThematicsRegexp
		  AND qq.score > show_limit() * (SELECT count(w) FROM q);
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_name)::int, 1.0::float8, 
			a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics
		  FROM auth_user AS a
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE g.role ILIKE 'recommender'
		  AND a.thematics ~* myThematicsRegexp;
  END IF;
END;
$_$;


--
-- TOC entry 260 (class 1255 OID 87785095)
-- Name: search_reviewers(text[], text[]); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION search_reviewers(mythematics text[], mywords text[]) RETURNS TABLE(id integer, num integer, score double precision, user_title character varying, first_name character varying, last_name character varying, uploaded_picture character varying, city character varying, country character varying, laboratory character varying, institution character varying, thematics character varying, roles character varying)
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
-- 		qcount(n) AS (
-- 			SELECT count(w) FROM q
-- 		),
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
			a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			array_to_string(array_agg(g.role ORDER BY g.role), ', ')::varchar(1024)
		  FROM auth_user AS a
		  JOIN qq ON a.id = qq.user_id
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE a.thematics ~* myThematicsRegexp
		  AND qq.score > show_limit() * (SELECT count(w) FROM q)
		  GROUP BY a.id, qq.score, a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution, a.thematics;
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_name)::int, 1.0::float8, 
			a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			array_to_string(array_agg(g.role ORDER BY g.role), ', ')::varchar(1024)
		  FROM auth_user AS a
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE a.thematics ~* myThematicsRegexp
		  GROUP BY a.id, a.user_title, a.first_name, a.last_name, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution, a.thematics;
  END IF;
END;
$_$;


--
-- TOC entry 227 (class 1255 OID 87778809)
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
-- TOC entry 252 (class 1255 OID 87778824)
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
-- TOC entry 253 (class 1255 OID 87782442)
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
		||coalesce(institution, '')||E'\n'||coalesce(thematics, '')||E'\n'))::text, ' '), '''', ''))
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
		||coalesce(institution, '')||E'\n'||coalesce(thematics, '')||E'\n'))::text, ' '), '''', ''))
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


SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 185 (class 1259 OID 87778677)
-- Name: auth_cas; Type: TABLE; Schema: public; Owner: -; Tablespace: 
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
-- TOC entry 184 (class 1259 OID 87778675)
-- Name: auth_cas_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_cas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2271 (class 0 OID 0)
-- Dependencies: 184
-- Name: auth_cas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_cas_id_seq OWNED BY auth_cas.id;


--
-- TOC entry 183 (class 1259 OID 87778661)
-- Name: auth_event; Type: TABLE; Schema: public; Owner: -; Tablespace: 
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
-- TOC entry 182 (class 1259 OID 87778659)
-- Name: auth_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2272 (class 0 OID 0)
-- Dependencies: 182
-- Name: auth_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_event_id_seq OWNED BY auth_event.id;


--
-- TOC entry 177 (class 1259 OID 87778616)
-- Name: auth_group; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE auth_group (
    id integer NOT NULL,
    role character varying(512),
    description text
);


--
-- TOC entry 176 (class 1259 OID 87778614)
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2273 (class 0 OID 0)
-- Dependencies: 176
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_group_id_seq OWNED BY auth_group.id;


--
-- TOC entry 179 (class 1259 OID 87778627)
-- Name: auth_membership; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE auth_membership (
    id integer NOT NULL,
    user_id integer,
    group_id integer
);


--
-- TOC entry 178 (class 1259 OID 87778625)
-- Name: auth_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2274 (class 0 OID 0)
-- Dependencies: 178
-- Name: auth_membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_membership_id_seq OWNED BY auth_membership.id;


--
-- TOC entry 181 (class 1259 OID 87778645)
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE auth_permission (
    id integer NOT NULL,
    group_id integer,
    name character varying(512),
    table_name character varying(512),
    record_id integer
);


--
-- TOC entry 180 (class 1259 OID 87778643)
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2275 (class 0 OID 0)
-- Dependencies: 180
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_permission_id_seq OWNED BY auth_permission.id;


--
-- TOC entry 175 (class 1259 OID 87778605)
-- Name: auth_user; Type: TABLE; Schema: public; Owner: -; Tablespace: 
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
    thematics character varying(1024)
);


--
-- TOC entry 174 (class 1259 OID 87778603)
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2276 (class 0 OID 0)
-- Dependencies: 174
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE auth_user_id_seq OWNED BY auth_user.id;


--
-- TOC entry 210 (class 1259 OID 87785137)
-- Name: scheduler_run; Type: TABLE; Schema: public; Owner: -; Tablespace: 
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
-- TOC entry 209 (class 1259 OID 87785135)
-- Name: scheduler_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2277 (class 0 OID 0)
-- Dependencies: 209
-- Name: scheduler_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_run_id_seq OWNED BY scheduler_run.id;


--
-- TOC entry 208 (class 1259 OID 87785124)
-- Name: scheduler_task; Type: TABLE; Schema: public; Owner: -; Tablespace: 
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
-- TOC entry 214 (class 1259 OID 87785166)
-- Name: scheduler_task_deps; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE scheduler_task_deps (
    id integer NOT NULL,
    job_name character varying(512),
    task_parent integer,
    task_child integer,
    can_visit character(1)
);


--
-- TOC entry 213 (class 1259 OID 87785164)
-- Name: scheduler_task_deps_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_task_deps_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2278 (class 0 OID 0)
-- Dependencies: 213
-- Name: scheduler_task_deps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_task_deps_id_seq OWNED BY scheduler_task_deps.id;


--
-- TOC entry 207 (class 1259 OID 87785122)
-- Name: scheduler_task_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_task_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2279 (class 0 OID 0)
-- Dependencies: 207
-- Name: scheduler_task_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_task_id_seq OWNED BY scheduler_task.id;


--
-- TOC entry 212 (class 1259 OID 87785153)
-- Name: scheduler_worker; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE scheduler_worker (
    id integer NOT NULL,
    worker_name character varying(255),
    first_heartbeat timestamp without time zone,
    last_heartbeat timestamp without time zone,
    status character varying(512),
    is_ticker character(1),
    group_names text,
    worker_stats json
);


--
-- TOC entry 211 (class 1259 OID 87785151)
-- Name: scheduler_worker_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE scheduler_worker_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2280 (class 0 OID 0)
-- Dependencies: 211
-- Name: scheduler_worker_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE scheduler_worker_id_seq OWNED BY scheduler_worker.id;


--
-- TOC entry 187 (class 1259 OID 87778693)
-- Name: t_articles; Type: TABLE; Schema: public; Owner: -; Tablespace: 
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
    last_status_change timestamp without time zone DEFAULT statement_timestamp()
);


--
-- TOC entry 186 (class 1259 OID 87778691)
-- Name: t_articles_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_articles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2281 (class 0 OID 0)
-- Dependencies: 186
-- Name: t_articles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_articles_id_seq OWNED BY t_articles.id;


--
-- TOC entry 201 (class 1259 OID 87784954)
-- Name: t_articles_words; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_articles_words (
    article_id integer NOT NULL,
    distinct_word_id integer NOT NULL,
    coef real DEFAULT 1.0
);


--
-- TOC entry 199 (class 1259 OID 87784943)
-- Name: t_distinct_words_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_distinct_words_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 200 (class 1259 OID 87784945)
-- Name: t_distinct_words; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_distinct_words (
    id integer DEFAULT nextval('t_distinct_words_id_seq'::regclass) NOT NULL,
    word character varying(250)
);


--
-- TOC entry 189 (class 1259 OID 87778704)
-- Name: t_thematics; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_thematics (
    id integer NOT NULL,
    keyword character varying(512)
);


--
-- TOC entry 188 (class 1259 OID 87778702)
-- Name: t_keywords_list_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_keywords_list_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2282 (class 0 OID 0)
-- Dependencies: 188
-- Name: t_keywords_list_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_keywords_list_id_seq OWNED BY t_thematics.id;


--
-- TOC entry 191 (class 1259 OID 87778731)
-- Name: t_recommendations; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_recommendations (
    id integer NOT NULL,
    article_id integer,
    recommendation_comments text,
    recommendation_timestamp timestamp without time zone DEFAULT statement_timestamp(),
    doi character varying(512),
    recommender_id integer,
    last_change timestamp without time zone DEFAULT statement_timestamp(),
    is_closed character(1) DEFAULT 'F'::bpchar NOT NULL,
    reply text
);


--
-- TOC entry 190 (class 1259 OID 87778729)
-- Name: t_recommendations_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_recommendations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2283 (class 0 OID 0)
-- Dependencies: 190
-- Name: t_recommendations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_recommendations_id_seq OWNED BY t_recommendations.id;


--
-- TOC entry 193 (class 1259 OID 87779009)
-- Name: t_reviews; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_reviews (
    id integer NOT NULL,
    recommendation_id integer,
    reviewer_id integer,
    anonymously character(1),
    review text,
    last_change timestamp without time zone DEFAULT statement_timestamp()
);


--
-- TOC entry 192 (class 1259 OID 87779007)
-- Name: t_reviewers_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_reviewers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2284 (class 0 OID 0)
-- Dependencies: 192
-- Name: t_reviewers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_reviewers_id_seq OWNED BY t_reviews.id;


--
-- TOC entry 198 (class 1259 OID 87782589)
-- Name: t_status_article; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_status_article (
    id integer NOT NULL,
    status character varying(50),
    color_class character varying(50),
    explaination text
);


--
-- TOC entry 197 (class 1259 OID 87782587)
-- Name: t_status_article_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_status_article_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2285 (class 0 OID 0)
-- Dependencies: 197
-- Name: t_status_article_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_status_article_id_seq OWNED BY t_status_article.id;


--
-- TOC entry 204 (class 1259 OID 87785000)
-- Name: t_suggested_recommenders; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_suggested_recommenders (
    id integer NOT NULL,
    article_id integer,
    suggested_recommender_id integer
);


--
-- TOC entry 203 (class 1259 OID 87784998)
-- Name: t_suggested_recommenders_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE t_suggested_recommenders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 2286 (class 0 OID 0)
-- Dependencies: 203
-- Name: t_suggested_recommenders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE t_suggested_recommenders_id_seq OWNED BY t_suggested_recommenders.id;


--
-- TOC entry 196 (class 1259 OID 87782424)
-- Name: t_user_words; Type: TABLE; Schema: public; Owner: -; Tablespace: 
--

CREATE TABLE t_user_words (
    id integer,
    word character varying(250),
    coef real DEFAULT 1.0
);


--
-- TOC entry 202 (class 1259 OID 87784993)
-- Name: v_last_recommendation; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_last_recommendation AS
 WITH q(id, last_recommendation, days_since_last_recommendation) AS (
         SELECT DISTINCT u.id,
            max(r.last_change) AS max,
            ((statement_timestamp())::date - (max(r.last_change))::date)
           FROM (auth_user u
             LEFT JOIN t_recommendations r ON ((u.id = r.recommender_id)))
          GROUP BY u.id
        UNION
         SELECT DISTINCT u.id,
            max(r.last_change) AS last_recommendation,
            ((statement_timestamp())::date - (max(r.last_change))::date) AS days_since_last_recommendation
           FROM (auth_user u
             LEFT JOIN t_reviews r ON ((u.id = r.reviewer_id)))
          GROUP BY u.id
        )
 SELECT q.id,
    max(q.last_recommendation) AS last_recommendation,
    min(q.days_since_last_recommendation) AS days_since_last_recommendation
   FROM q
  GROUP BY q.id;


--
-- TOC entry 206 (class 1259 OID 87785114)
-- Name: v_reviewers; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_reviewers AS
 SELECT r.id,
    array_to_string(array_agg(
        CASE
            WHEN ((au.id IS NOT NULL) AND ((rv.anonymously = 'F'::bpchar) OR (rv.anonymously IS NULL))) THEN ((COALESCE(((au.user_title)::text || ' '::text), ''::text) || COALESCE(((au.first_name)::text || ' '::text), ''::text)) || (COALESCE(au.last_name, ''::character varying))::text)
            WHEN (rv.anonymously = 'T'::bpchar) THEN 'Anonymous'::text
            ELSE ''::text
        END), ', '::text) AS reviewers
   FROM ((t_recommendations r
     LEFT JOIN t_reviews rv ON ((r.id = rv.recommendation_id)))
     LEFT JOIN auth_user au ON ((rv.reviewer_id = au.id)))
  GROUP BY r.id;


--
-- TOC entry 205 (class 1259 OID 87785026)
-- Name: v_suggested_recommenders; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW v_suggested_recommenders AS
 SELECT a.id,
    array_to_string(array_agg(((COALESCE(((au.user_title)::text || ' '::text), ''::text) || COALESCE(((au.first_name)::text || ' '::text), ''::text)) || (COALESCE(au.last_name, ''::character varying))::text)), ', '::text) AS suggested_recommenders
   FROM ((t_articles a
     LEFT JOIN t_suggested_recommenders sr ON ((a.id = sr.article_id)))
     LEFT JOIN auth_user au ON ((sr.suggested_recommender_id = au.id)))
  GROUP BY a.id;


--
-- TOC entry 2059 (class 2604 OID 87778680)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_cas ALTER COLUMN id SET DEFAULT nextval('auth_cas_id_seq'::regclass);


--
-- TOC entry 2058 (class 2604 OID 87778664)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_event ALTER COLUMN id SET DEFAULT nextval('auth_event_id_seq'::regclass);


--
-- TOC entry 2055 (class 2604 OID 87778619)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_group ALTER COLUMN id SET DEFAULT nextval('auth_group_id_seq'::regclass);


--
-- TOC entry 2056 (class 2604 OID 87778630)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_membership ALTER COLUMN id SET DEFAULT nextval('auth_membership_id_seq'::regclass);


--
-- TOC entry 2057 (class 2604 OID 87778648)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission ALTER COLUMN id SET DEFAULT nextval('auth_permission_id_seq'::regclass);


--
-- TOC entry 2053 (class 2604 OID 87778608)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_user ALTER COLUMN id SET DEFAULT nextval('auth_user_id_seq'::regclass);


--
-- TOC entry 2077 (class 2604 OID 87785140)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_run ALTER COLUMN id SET DEFAULT nextval('scheduler_run_id_seq'::regclass);


--
-- TOC entry 2076 (class 2604 OID 87785127)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task ALTER COLUMN id SET DEFAULT nextval('scheduler_task_id_seq'::regclass);


--
-- TOC entry 2079 (class 2604 OID 87785169)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task_deps ALTER COLUMN id SET DEFAULT nextval('scheduler_task_deps_id_seq'::regclass);


--
-- TOC entry 2078 (class 2604 OID 87785156)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_worker ALTER COLUMN id SET DEFAULT nextval('scheduler_worker_id_seq'::regclass);


--
-- TOC entry 2060 (class 2604 OID 87778696)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles ALTER COLUMN id SET DEFAULT nextval('t_articles_id_seq'::regclass);


--
-- TOC entry 2065 (class 2604 OID 87778734)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_recommendations ALTER COLUMN id SET DEFAULT nextval('t_recommendations_id_seq'::regclass);


--
-- TOC entry 2069 (class 2604 OID 87779012)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews ALTER COLUMN id SET DEFAULT nextval('t_reviewers_id_seq'::regclass);


--
-- TOC entry 2072 (class 2604 OID 87782592)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_status_article ALTER COLUMN id SET DEFAULT nextval('t_status_article_id_seq'::regclass);


--
-- TOC entry 2075 (class 2604 OID 87785003)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders ALTER COLUMN id SET DEFAULT nextval('t_suggested_recommenders_id_seq'::regclass);


--
-- TOC entry 2064 (class 2604 OID 87778707)
-- Name: id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_thematics ALTER COLUMN id SET DEFAULT nextval('t_keywords_list_id_seq'::regclass);


--
-- TOC entry 2091 (class 2606 OID 87778685)
-- Name: auth_cas_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY auth_cas
    ADD CONSTRAINT auth_cas_pkey PRIMARY KEY (id);


--
-- TOC entry 2089 (class 2606 OID 87778669)
-- Name: auth_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY auth_event
    ADD CONSTRAINT auth_event_pkey PRIMARY KEY (id);


--
-- TOC entry 2083 (class 2606 OID 87778624)
-- Name: auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- TOC entry 2085 (class 2606 OID 87778632)
-- Name: auth_membership_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY auth_membership
    ADD CONSTRAINT auth_membership_pkey PRIMARY KEY (id);


--
-- TOC entry 2087 (class 2606 OID 87778653)
-- Name: auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- TOC entry 2081 (class 2606 OID 87778613)
-- Name: auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- TOC entry 2123 (class 2606 OID 87785145)
-- Name: scheduler_run_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY scheduler_run
    ADD CONSTRAINT scheduler_run_pkey PRIMARY KEY (id);


--
-- TOC entry 2129 (class 2606 OID 87785174)
-- Name: scheduler_task_deps_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY scheduler_task_deps
    ADD CONSTRAINT scheduler_task_deps_pkey PRIMARY KEY (id);


--
-- TOC entry 2119 (class 2606 OID 87785132)
-- Name: scheduler_task_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY scheduler_task
    ADD CONSTRAINT scheduler_task_pkey PRIMARY KEY (id);


--
-- TOC entry 2121 (class 2606 OID 87785134)
-- Name: scheduler_task_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY scheduler_task
    ADD CONSTRAINT scheduler_task_uuid_key UNIQUE (uuid);


--
-- TOC entry 2125 (class 2606 OID 87785161)
-- Name: scheduler_worker_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY scheduler_worker
    ADD CONSTRAINT scheduler_worker_pkey PRIMARY KEY (id);


--
-- TOC entry 2127 (class 2606 OID 87785163)
-- Name: scheduler_worker_worker_name_key; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY scheduler_worker
    ADD CONSTRAINT scheduler_worker_worker_name_key UNIQUE (worker_name);


--
-- TOC entry 2093 (class 2606 OID 87778701)
-- Name: t_articles_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT t_articles_pkey PRIMARY KEY (id);


--
-- TOC entry 2107 (class 2606 OID 87784950)
-- Name: t_distinct_words_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_distinct_words
    ADD CONSTRAINT t_distinct_words_pkey PRIMARY KEY (id);


--
-- TOC entry 2110 (class 2606 OID 87784953)
-- Name: t_distinct_words_word_unique; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_distinct_words
    ADD CONSTRAINT t_distinct_words_word_unique UNIQUE (word);


--
-- TOC entry 2095 (class 2606 OID 87778712)
-- Name: t_keywords_list_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_thematics
    ADD CONSTRAINT t_keywords_list_pkey PRIMARY KEY (id);


--
-- TOC entry 2097 (class 2606 OID 87778736)
-- Name: t_recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_recommendations
    ADD CONSTRAINT t_recommendations_pkey PRIMARY KEY (id);


--
-- TOC entry 2100 (class 2606 OID 87779014)
-- Name: t_reviewers_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_reviews
    ADD CONSTRAINT t_reviewers_pkey PRIMARY KEY (id);


--
-- TOC entry 2103 (class 2606 OID 87782597)
-- Name: t_status_article_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_status_article
    ADD CONSTRAINT t_status_article_pkey PRIMARY KEY (id);


--
-- TOC entry 2105 (class 2606 OID 87782599)
-- Name: t_status_article_status_key; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_status_article
    ADD CONSTRAINT t_status_article_status_key UNIQUE (status);


--
-- TOC entry 2115 (class 2606 OID 87785005)
-- Name: t_suggested_recommenders_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT t_suggested_recommenders_pkey PRIMARY KEY (id);


--
-- TOC entry 2113 (class 2606 OID 87784959)
-- Name: tarticleswords_pkey; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_articles_words
    ADD CONSTRAINT tarticleswords_pkey PRIMARY KEY (distinct_word_id, article_id);


--
-- TOC entry 2117 (class 2606 OID 87785084)
-- Name: tsuggestedrecommenders_unique; Type: CONSTRAINT; Schema: public; Owner: -; Tablespace: 
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_unique UNIQUE (article_id, suggested_recommender_id);


--
-- TOC entry 2108 (class 1259 OID 87784951)
-- Name: t_distinct_words_word_idx; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX t_distinct_words_word_idx ON t_distinct_words USING btree (word);


--
-- TOC entry 2111 (class 1259 OID 87784971)
-- Name: tdistinctwords_gist; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX tdistinctwords_gist ON t_distinct_words USING gist (word gist_trgm_ops);


--
-- TOC entry 2098 (class 1259 OID 87785218)
-- Name: trecommendations_articleid_idx; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX trecommendations_articleid_idx ON t_recommendations USING btree (article_id);


--
-- TOC entry 2101 (class 1259 OID 87782433)
-- Name: tuserwords_idx; Type: INDEX; Schema: public; Owner: -; Tablespace: 
--

CREATE INDEX tuserwords_idx ON t_user_words USING gist (word gist_trgm_ops);


--
-- TOC entry 2153 (class 2620 OID 87785081)
-- Name: auto_last_change_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_last_change_trigger BEFORE INSERT OR DELETE OR UPDATE ON t_recommendations FOR EACH ROW EXECUTE PROCEDURE auto_last_change_trigger_function();


--
-- TOC entry 2154 (class 2620 OID 87785082)
-- Name: auto_last_change_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_last_change_trigger BEFORE INSERT OR DELETE OR UPDATE ON t_reviews FOR EACH ROW EXECUTE PROCEDURE auto_last_change_trigger_function();


--
-- TOC entry 2151 (class 2620 OID 87785080)
-- Name: auto_last_status_change_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_last_status_change_trigger BEFORE INSERT OR DELETE OR UPDATE OF status ON t_articles FOR EACH ROW EXECUTE PROCEDURE auto_last_status_change_trigger_function();


--
-- TOC entry 2152 (class 2620 OID 87782637)
-- Name: auto_nb_recommendations_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER auto_nb_recommendations_trigger AFTER INSERT OR DELETE OR UPDATE ON t_recommendations FOR EACH ROW EXECUTE PROCEDURE auto_nb_recommendations_trigger_function();


--
-- TOC entry 2150 (class 2620 OID 87785075)
-- Name: distinct_words_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER distinct_words_trigger AFTER INSERT OR DELETE OR UPDATE OF title, authors, keywords, abstract ON t_articles FOR EACH ROW EXECUTE PROCEDURE distinct_words_trigger_function();


--
-- TOC entry 2149 (class 2620 OID 87782453)
-- Name: user_words_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER user_words_trigger AFTER INSERT OR DELETE OR UPDATE OF first_name, last_name, city, country, laboratory, institution, thematics ON auth_user FOR EACH ROW EXECUTE PROCEDURE user_words_trigger_function();


--
-- TOC entry 2134 (class 2606 OID 87778686)
-- Name: auth_cas_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_cas
    ADD CONSTRAINT auth_cas_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;


--
-- TOC entry 2133 (class 2606 OID 87778670)
-- Name: auth_event_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_event
    ADD CONSTRAINT auth_event_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;


--
-- TOC entry 2131 (class 2606 OID 87778638)
-- Name: auth_membership_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_membership
    ADD CONSTRAINT auth_membership_group_id_fkey FOREIGN KEY (group_id) REFERENCES auth_group(id) ON DELETE CASCADE;


--
-- TOC entry 2130 (class 2606 OID 87778633)
-- Name: auth_membership_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_membership
    ADD CONSTRAINT auth_membership_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE;


--
-- TOC entry 2132 (class 2606 OID 87778654)
-- Name: auth_permission_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_group_id_fkey FOREIGN KEY (group_id) REFERENCES auth_group(id) ON DELETE CASCADE;


--
-- TOC entry 2147 (class 2606 OID 87785146)
-- Name: scheduler_run_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_run
    ADD CONSTRAINT scheduler_run_task_id_fkey FOREIGN KEY (task_id) REFERENCES scheduler_task(id) ON DELETE CASCADE;


--
-- TOC entry 2148 (class 2606 OID 87785175)
-- Name: scheduler_task_deps_task_child_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY scheduler_task_deps
    ADD CONSTRAINT scheduler_task_deps_task_child_fkey FOREIGN KEY (task_child) REFERENCES scheduler_task(id) ON DELETE CASCADE;


--
-- TOC entry 2136 (class 2606 OID 87779040)
-- Name: t_articles_suggested_recommender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT t_articles_suggested_recommender_id_fkey FOREIGN KEY (suggested_recommender_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2135 (class 2606 OID 87778800)
-- Name: t_articles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT t_articles_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2139 (class 2606 OID 87784977)
-- Name: t_recommendations_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_recommendations
    ADD CONSTRAINT t_recommendations_article_id_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON DELETE CASCADE;


--
-- TOC entry 2138 (class 2606 OID 87779025)
-- Name: t_recommendations_recommender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_recommendations
    ADD CONSTRAINT t_recommendations_recommender_id_fkey FOREIGN KEY (recommender_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2140 (class 2606 OID 87779015)
-- Name: t_reviewers_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews
    ADD CONSTRAINT t_reviewers_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES t_recommendations(id) ON DELETE CASCADE;


--
-- TOC entry 2141 (class 2606 OID 87779020)
-- Name: t_reviewers_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_reviews
    ADD CONSTRAINT t_reviewers_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES auth_user(id) ON DELETE RESTRICT;


--
-- TOC entry 2137 (class 2606 OID 87782619)
-- Name: tarticles_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles
    ADD CONSTRAINT tarticles_status_fkey FOREIGN KEY (status) REFERENCES t_status_article(status);


--
-- TOC entry 2143 (class 2606 OID 87784960)
-- Name: tarticleswords_tarticles_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles_words
    ADD CONSTRAINT tarticleswords_tarticles_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2144 (class 2606 OID 87784965)
-- Name: tarticleswords_tdistinctwords_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_articles_words
    ADD CONSTRAINT tarticleswords_tdistinctwords_fkey FOREIGN KEY (distinct_word_id) REFERENCES t_distinct_words(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2146 (class 2606 OID 87785011)
-- Name: tsuggestedrecommenders_authusers_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_authusers_fkey FOREIGN KEY (suggested_recommender_id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2145 (class 2606 OID 87785006)
-- Name: tsuggestedrecommenders_tarticles_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_tarticles_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2142 (class 2606 OID 87782428)
-- Name: tuserwords_authuser_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY t_user_words
    ADD CONSTRAINT tuserwords_authuser_fkey FOREIGN KEY (id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 2270 (class 0 OID 0)
-- Dependencies: 8
-- Name: public; Type: ACL; Schema: -; Owner: -
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2016-09-08 15:10:17 CEST

--
-- PostgreSQL database dump complete
--

