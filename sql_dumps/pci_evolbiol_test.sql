--
-- PostgreSQL database dump
--

-- Dumped from database version 10.16 (Ubuntu 10.16-0ubuntu0.18.04.1)
-- Dumped by pg_dump version 13.2 (Ubuntu 13.2-1.pgdg18.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: unaccent; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;


--
-- Name: EXTENSION unaccent; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION unaccent IS 'text search dictionary that removes accents';


--
-- Name: alert_last_recommended_article_ids_for_user(integer); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.alert_last_recommended_article_ids_for_user(userid integer) RETURNS integer[]
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
	--AND a.thematics ~* myThematicsRegexp /* to be activated later */
	INTO myIds;
  RETURN myIds;
END;
$_$;


ALTER FUNCTION public.alert_last_recommended_article_ids_for_user(userid integer) OWNER TO pci_admin;

--
-- Name: auto_last_change_recommendation_trigger_function(); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.auto_last_change_recommendation_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
      NEW.last_change = statement_timestamp();
      RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
      IF (coalesce(OLD.recommendation_state, '') NOT LIKE NEW.recommendation_state) /*OR (OLD.is_closed != NEW.is_closed)*/ THEN
          NEW.last_change = statement_timestamp();
      END IF;
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      RETURN OLD;
    END IF;
  END;
$$;


ALTER FUNCTION public.auto_last_change_recommendation_trigger_function() OWNER TO pci_admin;

--
-- Name: auto_last_change_review_trigger_function(); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.auto_last_change_review_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'INSERT') THEN
      NEW.last_change = statement_timestamp();
      RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
      IF NEW.review_state != OLD.review_state THEN
          NEW.last_change = statement_timestamp();
      END IF;
      RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
      RETURN OLD;
    END IF;
  END;
$$;


ALTER FUNCTION public.auto_last_change_review_trigger_function() OWNER TO pci_admin;

--
-- Name: auto_last_status_change_trigger_function(); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.auto_last_status_change_trigger_function() RETURNS trigger
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


ALTER FUNCTION public.auto_last_status_change_trigger_function() OWNER TO pci_admin;

--
-- Name: auto_nb_recommendations_trigger_function(); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.auto_nb_recommendations_trigger_function() RETURNS trigger
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


ALTER FUNCTION public.auto_nb_recommendations_trigger_function() OWNER TO pci_admin;

--
-- Name: colpivot(character varying, character varying, character varying[], character varying[], character varying, character varying); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.colpivot(out_table character varying, in_query character varying, key_cols character varying[], class_cols character varying[], value_e character varying, col_order character varying) RETURNS void
    LANGUAGE plpgsql
    AS $$
    declare
        in_table varchar;
        col varchar;
        ali varchar;
        on_e varchar;
        i integer;
        rec record;
        query varchar;
        -- This is actually an array of arrays but postgres does not support an array of arrays type so we flatten it.
        -- We could theoretically use the matrix feature but it's extremly cancerogenous and we would have to involve
        -- custom aggrigates. For most intents and purposes postgres does not have a multi-dimensional array type.
        clsc_cols text[] := array[]::text[];
        n_clsc_cols integer;
        n_class_cols integer;
    begin
        in_table := quote_ident('__' || out_table || '_in');
        execute ('create temp table ' || in_table || ' on commit drop as ' || in_query);
        -- get ordered unique columns (column combinations)
        query := 'select array[';
        i := 0;
        foreach col in array class_cols loop
            if i > 0 then
                query := query || ', ';
            end if;
            query := query || 'quote_literal(' || quote_ident(col) || ')';
            i := i + 1;
        end loop;
        query := query || '] x from ' || in_table;
        for j in 1..2 loop
            if j = 1 then
                query := query || ' group by ';
            else
                query := query || ' order by ';
                if col_order is not null then
                    query := query || col_order || ' ';
                    exit;
                end if;
            end if;
            i := 0;
            foreach col in array class_cols loop
                if i > 0 then
                    query := query || ', ';
                end if;
                query := query || quote_ident(col);
                i := i + 1;
            end loop;
        end loop;
        -- raise notice '%', query;
        for rec in
            execute query
        loop
            clsc_cols := array_cat(clsc_cols, rec.x);
        end loop;
        n_class_cols := array_length(class_cols, 1);
        n_clsc_cols := array_length(clsc_cols, 1) / n_class_cols;
        -- build target query
        query := 'select ';
        i := 0;
        foreach col in array key_cols loop
            if i > 0 then
                query := query || ', ';
            end if;
            query := query || '_key.' || quote_ident(col) || ' ';
            i := i + 1;
        end loop;
        for j in 1..n_clsc_cols loop
            query := query || ', ';
            col := '';
            for k in 1..n_class_cols loop
                if k > 1 then
                    col := col || ', ';
                end if;
                col := col || clsc_cols[(j - 1) * n_class_cols + k];
            end loop;
            ali := '_clsc_' || j::text;
            query := query || '(' || replace(value_e, '#', ali) || ')' || ' as ' || quote_ident(col) || ' ';
        end loop;
        query := query || ' from (select distinct ';
        i := 0;
        foreach col in array key_cols loop
            if i > 0 then
                query := query || ', ';
            end if;
            query := query || quote_ident(col) || ' ';
            i := i + 1;
        end loop;
        query := query || ' from ' || in_table || ') _key ';
        for j in 1..n_clsc_cols loop
            ali := '_clsc_' || j::text;
            on_e := '';
            i := 0;
            foreach col in array key_cols loop
                if i > 0 then
                    on_e := on_e || ' and ';
                end if;
                on_e := on_e || ali || '.' || quote_ident(col) || ' = _key.' || quote_ident(col) || ' ';
                i := i + 1;
            end loop;
            for k in 1..n_class_cols loop
                on_e := on_e || ' and ';
                on_e := on_e || ali || '.' || quote_ident(class_cols[k]) || ' = ' || clsc_cols[(j - 1) * n_class_cols + k];
            end loop;
            query := query || 'left join ' || in_table || ' as ' || ali || ' on ' || on_e || ' ';
        end loop;
        -- raise notice '%', query;
        execute ('create temp table ' || quote_ident(out_table) || ' on commit drop as ' || query);
        -- cleanup temporary in_table before we return
        execute ('drop table ' || in_table)
        return;
    end;
$$;


ALTER FUNCTION public.colpivot(out_table character varying, in_query character varying, key_cols character varying[], class_cols character varying[], value_e character varying, col_order character varying) OWNER TO pci_admin;

--
-- Name: distinct_words_trigger_function(); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.distinct_words_trigger_function() RETURNS trigger
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


ALTER FUNCTION public.distinct_words_trigger_function() OWNER TO pci_admin;

--
-- Name: get_distinct_word_id(character varying); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.get_distinct_word_id(myword character varying) RETURNS integer
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


ALTER FUNCTION public.get_distinct_word_id(myword character varying) OWNER TO pci_admin;

--
-- Name: propagate_field_deletion_function(); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.propagate_field_deletion_function() RETURNS trigger
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


ALTER FUNCTION public.propagate_field_deletion_function() OWNER TO pci_admin;

--
-- Name: search_articles(text[], text[], character varying, real, boolean); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.search_articles(mythematics text[], mywords text[], mystatus character varying DEFAULT 'Recommended'::character varying, mylimit real DEFAULT 0.4, all_by_default boolean DEFAULT false) RETURNS TABLE(id integer, num integer, score double precision, title text, authors text, article_source character varying, doi character varying, abstract text, upload_timestamp timestamp without time zone, thematics character varying, keywords text, auto_nb_recommendations integer, status character varying, last_status_change timestamp without time zone, uploaded_picture character varying, already_published boolean, anonymous_submission boolean, parallel_submission boolean)
    LANGUAGE plpgsql
    AS $_$
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
			a.anonymous_submission, a.parallel_submission
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
				a.anonymous_submission, a.parallel_submission
		FROM t_articles AS a
		WHERE a.status LIKE mystatus
		AND a.thematics ~* myThematicsRegexp;
  ELSE
	RETURN;
  END IF;
END;
$_$;


ALTER FUNCTION public.search_articles(mythematics text[], mywords text[], mystatus character varying, mylimit real, all_by_default boolean) OWNER TO pci_admin;

--
-- Name: search_articles_new(text[], text[], character varying, real, boolean); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.search_articles_new(mythematics text[], mywords text[], mystatus character varying DEFAULT '''Recommended''::character varying'::character varying, mylimit real DEFAULT '0.400000006'::real, all_by_default boolean DEFAULT false) RETURNS TABLE(id integer, num integer, score double precision, title text, authors text, article_source character varying, doi character varying, abstract text, upload_timestamp timestamp without time zone, thematics character varying, keywords text, auto_nb_recommendations integer, status character varying, last_status_change timestamp without time zone, uploaded_picture character varying, already_published boolean, anonymous_submission boolean, parallel_submission boolean, art_stage_1_id integer)
    LANGUAGE plpgsql
    AS $_$
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
$_$;


ALTER FUNCTION public.search_articles_new(mythematics text[], mywords text[], mystatus character varying, mylimit real, all_by_default boolean) OWNER TO pci_admin;

--
-- Name: search_recommenders(text[], text[], integer[]); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.search_recommenders(mythematics text[], mywords text[], exclude integer[] DEFAULT ARRAY[]::integer[]) RETURNS TABLE(id integer, num integer, score double precision, first_name character varying, last_name character varying, email character varying, uploaded_picture character varying, city character varying, country character varying, laboratory character varying, institution character varying, thematics character varying, excluded boolean)
    LANGUAGE plpgsql
    AS $_$
DECLARE
  myThematicsRegexp text;
BEGIN
  IF array_length(myThematics, 1) > 0 THEN
	myThematicsRegexp := '('|| array_to_string(myThematics, ')|(') ||')|(\|{2})';
  ELSE
	myThematicsRegexp := '\|{2}';
  END IF;
  raise WARNING 'myThematicsRegexp=%', myThematicsRegexp;
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
			a.id = ANY(exclude) AS excluded
		  FROM auth_user AS a
		  JOIN qq ON a.id = qq.user_id
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE g.role ILIKE 'recommender'
		  AND (a.thematics ~* myThematicsRegexp)
		  AND a.registration_key = ''
		  --AND qq.score > show_limit() * (SELECT count(w) FROM q)
		  ORDER BY qq.score DESC;
  ELSE
	RETURN QUERY SELECT a.id, row_number() OVER (ORDER BY a.last_name)::int, 1.0::float8, 
			a.first_name, a.last_name, a.email, a.uploaded_picture, a.city, a.country, a.laboratory, a.institution,
			replace(regexp_replace(a.thematics, '(^\|)|([\| \r\n]*$)', '', 'g'), '|', ', ')::varchar(1024) AS thematics,
			a.id = ANY(exclude) AS excluded
		  FROM auth_user AS a
		  JOIN auth_membership AS m ON a.id = m.user_id
		  JOIN auth_group AS g ON m.group_id = g.id
		  WHERE g.role ILIKE 'recommender'
		  AND a.registration_key = ''
		  AND (a.thematics ~* myThematicsRegexp);
  END IF;
END;
$_$;


ALTER FUNCTION public.search_recommenders(mythematics text[], mywords text[], exclude integer[]) OWNER TO pci_admin;

--
-- Name: set_auto_keywords(integer); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.set_auto_keywords(my_id integer) RETURNS void
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


ALTER FUNCTION public.set_auto_keywords(my_id integer) OWNER TO pci_admin;

--
-- Name: set_auto_nb_agreements(integer); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.set_auto_nb_agreements(my_id integer) RETURNS void
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


ALTER FUNCTION public.set_auto_nb_agreements(my_id integer) OWNER TO pci_admin;

--
-- Name: set_auto_nb_recommendations(integer); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.set_auto_nb_recommendations(my_id integer) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
  nb integer;
BEGIN
  SELECT count(*) FROM t_recommendations WHERE article_id = my_id INTO nb;
  UPDATE t_articles SET auto_nb_recommendations = nb WHERE id = my_id;
END;
$$;


ALTER FUNCTION public.set_auto_nb_recommendations(my_id integer) OWNER TO pci_admin;

--
-- Name: user_words_trigger_function(); Type: FUNCTION; Schema: public; Owner: pci_admin
--

CREATE FUNCTION public.user_words_trigger_function() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
  BEGIN
    IF (TG_OP = 'DELETE') THEN
        DELETE FROM t_user_words WHERE id = OLD.id;
        RETURN OLD;
    END IF;
    IF (TG_OP = 'UPDATE') THEN
        DELETE FROM t_user_words WHERE id = OLD.id;
    END IF;
    IF (TG_OP = 'INSERT') or (TG_OP = 'UPDATE') THEN
	WITH w(id, coef, word) AS (
	    SELECT DISTINCT a.id, 1.0, unaccent(replace(regexp_split_to_table(strip(to_tsvector('simple',
		coalesce(first_name, '')||E'\n'||coalesce(last_name, '')||E'\n'
		||coalesce(city, '')||E'\n'||coalesce(country, '')||E'\n'
		||coalesce(laboratory, '')||E'\n'||coalesce(institution, '')||E'\n'
		||coalesce(thematics, '')||E'\n'||coalesce(cv, '')||E'\n'
		||coalesce(keywords, '')||E'\n'
		))::text, ' '), '''', ''))
	    FROM auth_user AS a WHERE a.id = NEW.id
	)
	INSERT INTO t_user_words (id, coef, word)
	    SELECT id, max(coef), word
	    FROM w
	    GROUP BY id, word;
      RETURN NEW;
    END IF;
  END;
$$;


ALTER FUNCTION public.user_words_trigger_function() OWNER TO pci_admin;

SET default_tablespace = '';

--
-- Name: auth_cas; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.auth_cas (
    id integer NOT NULL,
    user_id integer,
    created_on timestamp without time zone,
    service character varying(512),
    ticket character varying(512),
    renew character(1)
);


ALTER TABLE public.auth_cas OWNER TO pci_admin;

--
-- Name: auth_cas_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.auth_cas_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_cas_id_seq OWNER TO pci_admin;

--
-- Name: auth_cas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.auth_cas_id_seq OWNED BY public.auth_cas.id;


--
-- Name: auth_event; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.auth_event (
    id integer NOT NULL,
    time_stamp timestamp without time zone,
    client_ip character varying(512),
    user_id integer,
    origin character varying(512),
    description text
);


ALTER TABLE public.auth_event OWNER TO pci_admin;

--
-- Name: auth_event_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.auth_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_event_id_seq OWNER TO pci_admin;

--
-- Name: auth_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.auth_event_id_seq OWNED BY public.auth_event.id;


--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.auth_group (
    id integer NOT NULL,
    role character varying(512),
    description text
);


ALTER TABLE public.auth_group OWNER TO pci_admin;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_id_seq OWNER TO pci_admin;

--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.auth_group_id_seq OWNED BY public.auth_group.id;


--
-- Name: auth_membership; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.auth_membership (
    id integer NOT NULL,
    user_id integer,
    group_id integer
);


ALTER TABLE public.auth_membership OWNER TO pci_admin;

--
-- Name: auth_membership_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.auth_membership_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_membership_id_seq OWNER TO pci_admin;

--
-- Name: auth_membership_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.auth_membership_id_seq OWNED BY public.auth_membership.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.auth_permission (
    id integer NOT NULL,
    group_id integer,
    name character varying(512),
    table_name character varying(512),
    record_id integer
);


ALTER TABLE public.auth_permission OWNER TO pci_admin;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_permission_id_seq OWNER TO pci_admin;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.auth_permission_id_seq OWNED BY public.auth_permission.id;


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.auth_user (
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
    alerts character varying(512) DEFAULT '||'::character varying,
    thematics character varying(1024) DEFAULT '||'::character varying,
    cv text,
    keywords VARCHAR(1024),
    website VARCHAR(4096),
    last_alert timestamp without time zone,
    registration_datetime timestamp without time zone DEFAULT statement_timestamp(),
    ethical_code_approved boolean DEFAULT false NOT NULL,
    recover_email character varying(512),
    recover_email_key character varying(512)
);


ALTER TABLE public.auth_user OWNER TO pci_admin;

--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_id_seq OWNER TO pci_admin;

--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;


--
-- Name: help_texts; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.help_texts (
    id integer NOT NULL,
    hashtag character varying(128),
    lang character varying(10) DEFAULT 'default'::character varying,
    contents text
);


ALTER TABLE public.help_texts OWNER TO pci_admin;

--
-- Name: help_texts_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.help_texts_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.help_texts_id_seq OWNER TO pci_admin;

--
-- Name: help_texts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.help_texts_id_seq OWNED BY public.help_texts.id;


--
-- Name: mail_queue; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.mail_queue (
    id integer NOT NULL,
    sending_status character varying(128),
    sending_attempts integer,
    sending_date timestamp without time zone,
    dest_mail_address character varying(256),
    user_id integer,
    article_id integer,
    recommendation_id integer,
    mail_subject character varying(256),
    mail_content text,
    mail_template_hashtag character varying(128),
    reminder_count integer,
    removed_from_queue boolean DEFAULT false,
    cc_mail_addresses character varying(1024)
);


ALTER TABLE public.mail_queue OWNER TO pci_admin;

ALTER TABLE public.mail_queue ADD COLUMN  IF NOT EXISTS replyto_addresses character varying(1024);

--
-- Name: mail_queue_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.mail_queue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.mail_queue_id_seq OWNER TO pci_admin;

--
-- Name: mail_queue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.mail_queue_id_seq OWNED BY public.mail_queue.id;


--
-- Name: mail_templates; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.mail_templates (
    id integer NOT NULL,
    hashtag character varying(128),
    lang character varying(10),
    subject character varying(256),
    description character varying(512),
    contents text
);


ALTER TABLE public.mail_templates OWNER TO pci_admin;

--
-- Name: mail_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.mail_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.mail_templates_id_seq OWNER TO pci_admin;

--
-- Name: mail_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.mail_templates_id_seq OWNED BY public.mail_templates.id;


--
-- Name: scheduler_run; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.scheduler_run (
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


ALTER TABLE public.scheduler_run OWNER TO pci_admin;

--
-- Name: scheduler_run_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.scheduler_run_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scheduler_run_id_seq OWNER TO pci_admin;

--
-- Name: scheduler_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.scheduler_run_id_seq OWNED BY public.scheduler_run.id;


--
-- Name: scheduler_task; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.scheduler_task (
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


ALTER TABLE public.scheduler_task OWNER TO pci_admin;

--
-- Name: scheduler_task_deps; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.scheduler_task_deps (
    id integer NOT NULL,
    job_name character varying(512),
    task_parent integer,
    task_child integer,
    can_visit character(1)
);


ALTER TABLE public.scheduler_task_deps OWNER TO pci_admin;

--
-- Name: scheduler_task_deps_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.scheduler_task_deps_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scheduler_task_deps_id_seq OWNER TO pci_admin;

--
-- Name: scheduler_task_deps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.scheduler_task_deps_id_seq OWNED BY public.scheduler_task_deps.id;


--
-- Name: scheduler_task_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.scheduler_task_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scheduler_task_id_seq OWNER TO pci_admin;

--
-- Name: scheduler_task_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.scheduler_task_id_seq OWNED BY public.scheduler_task.id;


--
-- Name: scheduler_worker; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.scheduler_worker (
    id integer NOT NULL,
    worker_name character varying(255),
    first_heartbeat timestamp without time zone,
    last_heartbeat timestamp without time zone,
    status character varying(512),
    is_ticker character(1),
    group_names text,
    worker_stats text
);


ALTER TABLE public.scheduler_worker OWNER TO pci_admin;

--
-- Name: scheduler_worker_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.scheduler_worker_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scheduler_worker_id_seq OWNER TO pci_admin;

--
-- Name: scheduler_worker_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.scheduler_worker_id_seq OWNED BY public.scheduler_worker.id;


--
-- Name: t_articles; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_articles (
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
    already_published boolean DEFAULT false,
    picture_data bytea,
    uploaded_picture character varying(512),
    picture_rights_ok boolean DEFAULT false,
    ms_version character varying(1024) DEFAULT ''::character varying,
    anonymous_submission boolean DEFAULT false,
    has_manager_in_authors BOOLEAN DEFAULT false,
    cover_letter text,
    parallel_submission boolean DEFAULT false,
    is_searching_reviewers boolean DEFAULT false,
    art_stage_1_id integer,
    scheduled_submission_date date,
    report_stage character varying(128),
    sub_thematics character varying(128),
    record_url_version character varying(128),
    record_id_version character varying(128)
);


ALTER TABLE public.t_articles OWNER TO pci_admin;

ALTER TABLE public.t_articles 
ADD COLUMN  IF NOT EXISTS no_results_based_on_data  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS results_based_on_data  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS data_doi character varying(512),
ADD COLUMN  IF NOT EXISTS no_scripts_used_for_result  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS scripts_used_for_result  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS scripts_doi character varying(512),
ADD COLUMN  IF NOT EXISTS no_codes_used_in_study  boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS codes_used_in_study boolean DEFAULT false,
ADD COLUMN  IF NOT EXISTS codes_doi character varying(512);

--
-- Name: t_articles_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_articles_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_articles_id_seq OWNER TO pci_admin;

--
-- Name: t_articles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_articles_id_seq OWNED BY public.t_articles.id;


--
-- Name: t_articles_words; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_articles_words (
    article_id integer NOT NULL,
    distinct_word_id integer NOT NULL,
    coef real DEFAULT 1.0
);


ALTER TABLE public.t_articles_words OWNER TO pci_admin;

--
-- Name: t_comments; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_comments (
    id integer NOT NULL,
    article_id integer,
    parent_id integer,
    user_id integer,
    user_comment text,
    comment_datetime timestamp without time zone DEFAULT statement_timestamp()
);


ALTER TABLE public.t_comments OWNER TO pci_admin;

--
-- Name: t_comments_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_comments_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_comments_id_seq OWNER TO pci_admin;

--
-- Name: t_comments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_comments_id_seq OWNED BY public.t_comments.id;


--
-- Name: t_distinct_words_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_distinct_words_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_distinct_words_id_seq OWNER TO pci_admin;

--
-- Name: t_distinct_words; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_distinct_words (
    id integer DEFAULT nextval('public.t_distinct_words_id_seq'::regclass) NOT NULL,
    word text
);


ALTER TABLE public.t_distinct_words OWNER TO pci_admin;

--
-- Name: t_thematics; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_thematics (
    id integer NOT NULL,
    keyword character varying(512)
);


ALTER TABLE public.t_thematics OWNER TO pci_admin;

--
-- Name: t_keywords_list_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_keywords_list_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_keywords_list_id_seq OWNER TO pci_admin;

--
-- Name: t_keywords_list_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_keywords_list_id_seq OWNED BY public.t_thematics.id;


--
-- Name: t_pdf; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_pdf (
    id integer NOT NULL,
    recommendation_id integer,
    pdf character varying(512),
    pdf_data bytea
);


ALTER TABLE public.t_pdf OWNER TO pci_admin;

--
-- Name: t_pdf_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_pdf_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_pdf_id_seq OWNER TO pci_admin;

--
-- Name: t_pdf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_pdf_id_seq OWNED BY public.t_pdf.id;


--
-- Name: t_press_reviews; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_press_reviews (
    id integer NOT NULL,
    recommendation_id integer,
    contributor_id integer
);


ALTER TABLE public.t_press_reviews OWNER TO pci_admin;

--
-- Name: t_press_review_contributors_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_press_review_contributors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_press_review_contributors_id_seq OWNER TO pci_admin;

--
-- Name: t_press_review_contributors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_press_review_contributors_id_seq OWNED BY public.t_press_reviews.id;


--
-- Name: t_recommendations; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_recommendations (
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
    recommendation_state character varying(50) DEFAULT 'Ongoing'::character varying,
    reply_pdf character varying(512),
    reply_pdf_data bytea,
    track_change character varying(512),
    track_change_data bytea,
    ms_version character varying(1024) DEFAULT ''::character varying,
    recommender_file character varying(512),
    recommender_file_data bytea
);


ALTER TABLE public.t_recommendations OWNER TO pci_admin;

--
-- Name: t_recommendations_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_recommendations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_recommendations_id_seq OWNER TO pci_admin;

--
-- Name: t_recommendations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_recommendations_id_seq OWNED BY public.t_recommendations.id;


--
-- Name: t_report_survey; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_report_survey (
    id integer NOT NULL,
    article_id integer,
    q1 character varying(1024),
    q2 character varying(1024),
    q3 character varying(1024),
    q4 boolean,
    q5 text,
    q6 character varying(1024),
    q7 character varying(1024),
    q8 character varying(1024),
    q9 character varying(1024),
    q10 date,
    q11 character varying(128),
    q11_details text,
    q12 character varying(128),
    q12_details text,
    q13 character varying(512),
    q13_details text,
    q14 boolean,
    q15 text,
    q16 character varying(128),
    q17 character varying(128),
    q18 boolean,
    q19 boolean,
    q20 character varying(128),
    q21 character varying(128),
    q22 character varying(128),
    q23 character varying(128),
    q24 date,
    q24_1 character varying(128),
    q24_1_details text,
    q25 boolean,
    q26 character varying(512),
    q26_details text,
    q27 character varying(512),
    q27_details text,
    q28 character varying(512),
    q28_details text,
    q29 boolean,
    q30 character varying(256),
    q31 character varying(128),
    q32 boolean,
    q1_1 character varying(1024),
    q1_2 character varying(256),

    temp_art_stage_1_id integer
);


ALTER TABLE public.t_report_survey OWNER TO pci_admin;

--
-- Name: t_report_survey_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_report_survey_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_report_survey_id_seq OWNER TO pci_admin;

--
-- Name: t_report_survey_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_report_survey_id_seq OWNED BY public.t_report_survey.id;


--
-- Name: t_resources; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_resources (
    id integer NOT NULL,
    resource_rank integer,
    resource_category character varying(250),
    resource_name character varying(512),
    resource_description text,
    resource_logo character varying(512),
    resource_logo_data bytea,
    resource_document character varying(512),
    resource_document_data bytea
);


ALTER TABLE public.t_resources OWNER TO pci_admin;

--
-- Name: t_resources_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_resources_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_resources_id_seq OWNER TO pci_admin;

--
-- Name: t_resources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_resources_id_seq OWNED BY public.t_resources.id;


--
-- Name: t_reviews; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_reviews (
    id integer NOT NULL,
    recommendation_id integer,
    reviewer_id integer,
    review text,
    last_change timestamp without time zone DEFAULT statement_timestamp(),
    is_closed boolean DEFAULT false,
    anonymously boolean DEFAULT false,
    review_state character varying(50),
    no_conflict_of_interest boolean,
    review_pdf character varying(512),
    review_pdf_data bytea,
    acceptation_timestamp timestamp without time zone,
    quick_decline_key character varying(512),
    reviewer_details character varying(512),
    emailing text
);


ALTER TABLE public.t_reviews OWNER TO pci_admin;

--
-- Name: t_reviewers_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_reviewers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_reviewers_id_seq OWNER TO pci_admin;

--
-- Name: t_reviewers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_reviewers_id_seq OWNED BY public.t_reviews.id;


--
-- Name: t_status_article; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_status_article (
    id integer NOT NULL,
    status character varying(50),
    color_class character varying(50),
    explaination text,
    priority_level character(1)
);


ALTER TABLE public.t_status_article OWNER TO pci_admin;

--
-- Name: t_status_article_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_status_article_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_status_article_id_seq OWNER TO pci_admin;

--
-- Name: t_status_article_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_status_article_id_seq OWNED BY public.t_status_article.id;


--
-- Name: t_suggested_recommenders; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_suggested_recommenders (
    id integer NOT NULL,
    article_id integer,
    suggested_recommender_id integer,
    email_sent boolean DEFAULT false,
    declined boolean DEFAULT false,
    emailing text
);


ALTER TABLE public.t_suggested_recommenders OWNER TO pci_admin;

--
-- Name: t_suggested_recommenders_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_suggested_recommenders_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_suggested_recommenders_id_seq OWNER TO pci_admin;

--
-- Name: t_suggested_recommenders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_suggested_recommenders_id_seq OWNED BY public.t_suggested_recommenders.id;


--
-- Name: t_supports_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_supports_id_seq
    START WITH 20
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_supports_id_seq OWNER TO pci_admin;

--
-- Name: t_supports; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_supports (
    id integer DEFAULT nextval('public.t_supports_id_seq'::regclass) NOT NULL,
    support_rank integer,
    support_name character varying(512),
    support_url character varying(512),
    support_logo character varying(512),
    support_logo_data bytea,
    support_category character varying(250)
);


ALTER TABLE public.t_supports OWNER TO pci_admin;

--
-- Name: t_user_words; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_user_words (
    id integer,
    word character varying(250),
    coef real DEFAULT 1.0
);


ALTER TABLE public.t_user_words OWNER TO pci_admin;

--
-- Name: t_coar_notification; Type: TABLE; Schema: public; Owner: pci_admin
--

CREATE TABLE public.t_coar_notification (
    id integer NOT NULL,
    created timestamp without time zone NOT NULL,
    rdf_type character varying NOT NULL,
    body character varying NOT NULL,
    direction character varying NOT NULL,
    http_status integer,
    inbox_url character varying NOT NULL
);


ALTER TABLE public.t_coar_notification OWNER TO pci_admin;

--
-- Name: t_coar_notification_id_seq; Type: SEQUENCE; Schema: public; Owner: pci_admin
--

CREATE SEQUENCE public.t_coar_notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.t_coar_notification_id_seq OWNER TO pci_admin;

--
-- Name: t_coar_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: pci_admin
--

ALTER SEQUENCE public.t_coar_notification_id_seq OWNED BY public.t_coar_notification.id;


--
-- Name: t_coar_notification id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_coar_notification ALTER COLUMN id SET DEFAULT nextval('public.t_coar_notification_id_seq'::regclass);

--
-- Name: v_article_recommender; Type: VIEW; Schema: public; Owner: pci_admin
--

CREATE VIEW public.v_article_recommender AS
 SELECT a.id,
    array_to_string(array_agg(DISTINCT (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text)), ', '::text) AS recommender
   FROM ((public.t_articles a
     LEFT JOIN public.t_recommendations r ON (((a.id = r.article_id) AND (r.is_closed IS FALSE))))
     LEFT JOIN public.auth_user au ON ((r.recommender_id = au.id)))
  GROUP BY a.id;


ALTER TABLE public.v_article_recommender OWNER TO pci_admin;

--
-- Name: v_last_recommendation; Type: VIEW; Schema: public; Owner: pci_admin
--

CREATE VIEW public.v_last_recommendation AS
 SELECT DISTINCT u.id,
    max(r.last_change) AS last_recommendation,
    ((statement_timestamp())::date - (max(r.last_change))::date) AS days_since_last_recommendation
   FROM (public.auth_user u
     LEFT JOIN public.t_recommendations r ON ((u.id = r.recommender_id)))
  GROUP BY u.id;


ALTER TABLE public.v_last_recommendation OWNER TO pci_admin;

--
-- Name: v_recommendation_contributors; Type: VIEW; Schema: public; Owner: pci_admin
--

CREATE VIEW public.v_recommendation_contributors AS
 SELECT r.id,
    array_to_string(array_agg(DISTINCT (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text)), ', '::text) AS contributors
   FROM ((public.t_recommendations r
     LEFT JOIN public.t_press_reviews c ON ((c.recommendation_id = r.id)))
     LEFT JOIN public.auth_user au ON ((c.contributor_id = au.id)))
  GROUP BY r.id;


ALTER TABLE public.v_recommendation_contributors OWNER TO pci_admin;

--
-- Name: v_reviewers; Type: VIEW; Schema: public; Owner: pci_admin
--

CREATE VIEW public.v_reviewers AS
 SELECT r.id,
    array_to_string(array_agg(
        CASE
            WHEN ((au.id IS NOT NULL) AND ((rv.anonymously IS FALSE) OR (rv.anonymously IS NULL))) THEN ((COALESCE(((au.user_title)::text || ' '::text), ''::text) || COALESCE(((au.first_name)::text || ' '::text), ''::text)) || (COALESCE(au.last_name, ''::character varying))::text)
            WHEN (rv.anonymously IS TRUE) THEN 'Anonymous'::text
            ELSE ''::text
        END), ', '::text) AS reviewers
   FROM ((public.t_recommendations r
     LEFT JOIN public.t_reviews rv ON ((r.id = rv.recommendation_id)))
     LEFT JOIN public.auth_user au ON ((rv.reviewer_id = au.id)))
  GROUP BY r.id;


ALTER TABLE public.v_reviewers OWNER TO pci_admin;

--
-- Name: v_reviewers_named; Type: VIEW; Schema: public; Owner: pci_admin
--

CREATE VIEW public.v_reviewers_named AS
 SELECT r.id,
    array_to_string(array_agg(
        CASE
            WHEN ((rv.id IS NOT NULL) AND (au.id IS NOT NULL)) THEN (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text)
            WHEN ((rv.id IS NOT NULL) AND (au.id IS NULL)) THEN '[Unnamed]'::text
            ELSE ''::text
        END), ', '::text) AS reviewers
   FROM ((public.t_recommendations r
     LEFT JOIN public.t_reviews rv ON ((r.id = rv.recommendation_id)))
     LEFT JOIN public.auth_user au ON ((rv.reviewer_id = au.id)))
  GROUP BY r.id;


ALTER TABLE public.v_reviewers_named OWNER TO pci_admin;

--
-- Name: v_roles; Type: VIEW; Schema: public; Owner: pci_admin
--

CREATE VIEW public.v_roles AS
 SELECT auth_user.id,
    (array_to_string(array_agg(auth_group.role), ', '::text))::character varying(512) AS roles
   FROM ((public.auth_user
     LEFT JOIN public.auth_membership ON ((auth_membership.user_id = auth_user.id)))
     LEFT JOIN public.auth_group ON ((auth_group.id = auth_membership.group_id)))
  GROUP BY auth_user.id;


ALTER TABLE public.v_roles OWNER TO pci_admin;

--
-- Name: v_suggested_recommenders; Type: VIEW; Schema: public; Owner: pci_admin
--

CREATE VIEW public.v_suggested_recommenders AS
 SELECT a.id,
    array_to_string(array_agg(DISTINCT (COALESCE(((au.first_name)::text || ' '::text), ''::text) || (COALESCE(au.last_name, ''::character varying))::text)), ', '::text) AS suggested_recommenders
   FROM ((public.t_articles a
     LEFT JOIN public.t_suggested_recommenders sr ON ((a.id = sr.article_id)))
     LEFT JOIN public.auth_user au ON ((sr.suggested_recommender_id = au.id)))
  GROUP BY a.id;


ALTER TABLE public.v_suggested_recommenders OWNER TO pci_admin;

--
-- Name: auth_cas id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_cas ALTER COLUMN id SET DEFAULT nextval('public.auth_cas_id_seq'::regclass);


--
-- Name: auth_event id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_event ALTER COLUMN id SET DEFAULT nextval('public.auth_event_id_seq'::regclass);


--
-- Name: auth_group id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_group ALTER COLUMN id SET DEFAULT nextval('public.auth_group_id_seq'::regclass);


--
-- Name: auth_membership id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_membership ALTER COLUMN id SET DEFAULT nextval('public.auth_membership_id_seq'::regclass);


--
-- Name: auth_permission id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_permission ALTER COLUMN id SET DEFAULT nextval('public.auth_permission_id_seq'::regclass);


--
-- Name: auth_user id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_user ALTER COLUMN id SET DEFAULT nextval('public.auth_user_id_seq'::regclass);


--
-- Name: help_texts id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.help_texts ALTER COLUMN id SET DEFAULT nextval('public.help_texts_id_seq'::regclass);


--
-- Name: mail_queue id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.mail_queue ALTER COLUMN id SET DEFAULT nextval('public.mail_queue_id_seq'::regclass);


--
-- Name: mail_templates id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.mail_templates ALTER COLUMN id SET DEFAULT nextval('public.mail_templates_id_seq'::regclass);


--
-- Name: scheduler_run id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_run ALTER COLUMN id SET DEFAULT nextval('public.scheduler_run_id_seq'::regclass);


--
-- Name: scheduler_task id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_task ALTER COLUMN id SET DEFAULT nextval('public.scheduler_task_id_seq'::regclass);


--
-- Name: scheduler_task_deps id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_task_deps ALTER COLUMN id SET DEFAULT nextval('public.scheduler_task_deps_id_seq'::regclass);


--
-- Name: scheduler_worker id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_worker ALTER COLUMN id SET DEFAULT nextval('public.scheduler_worker_id_seq'::regclass);


--
-- Name: t_articles id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles ALTER COLUMN id SET DEFAULT nextval('public.t_articles_id_seq'::regclass);


--
-- Name: t_comments id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_comments ALTER COLUMN id SET DEFAULT nextval('public.t_comments_id_seq'::regclass);


--
-- Name: t_pdf id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_pdf ALTER COLUMN id SET DEFAULT nextval('public.t_pdf_id_seq'::regclass);


--
-- Name: t_press_reviews id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_press_reviews ALTER COLUMN id SET DEFAULT nextval('public.t_press_review_contributors_id_seq'::regclass);


--
-- Name: t_recommendations id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_recommendations ALTER COLUMN id SET DEFAULT nextval('public.t_recommendations_id_seq'::regclass);


--
-- Name: t_report_survey id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_report_survey ALTER COLUMN id SET DEFAULT nextval('public.t_report_survey_id_seq'::regclass);


--
-- Name: t_resources id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_resources ALTER COLUMN id SET DEFAULT nextval('public.t_resources_id_seq'::regclass);


--
-- Name: t_reviews id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_reviews ALTER COLUMN id SET DEFAULT nextval('public.t_reviewers_id_seq'::regclass);


--
-- Name: t_status_article id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_status_article ALTER COLUMN id SET DEFAULT nextval('public.t_status_article_id_seq'::regclass);


--
-- Name: t_suggested_recommenders id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_suggested_recommenders ALTER COLUMN id SET DEFAULT nextval('public.t_suggested_recommenders_id_seq'::regclass);


--
-- Name: t_thematics id; Type: DEFAULT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_thematics ALTER COLUMN id SET DEFAULT nextval('public.t_keywords_list_id_seq'::regclass);


--
-- Name: auth_cas auth_cas_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_cas
    ADD CONSTRAINT auth_cas_pkey PRIMARY KEY (id);


--
-- Name: auth_event auth_event_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_event
    ADD CONSTRAINT auth_event_pkey PRIMARY KEY (id);


--
-- Name: auth_group auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_membership auth_membership_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_membership
    ADD CONSTRAINT auth_membership_pkey PRIMARY KEY (id);


--
-- Name: auth_permission auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user auth_user_recover_email_key; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_recover_email_key UNIQUE (recover_email);


--
-- Name: auth_user auth_user_recover_email_key_key; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_recover_email_key_key UNIQUE (recover_email_key);


--
-- Name: auth_user authuser_email_unique; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT authuser_email_unique UNIQUE (email);


--
-- Name: help_texts help_texts_language_hashtag_unique; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.help_texts
    ADD CONSTRAINT help_texts_language_hashtag_unique UNIQUE (lang, hashtag);


--
-- Name: help_texts help_texts_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.help_texts
    ADD CONSTRAINT help_texts_pkey PRIMARY KEY (id);


--
-- Name: mail_queue mail_queue_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.mail_queue
    ADD CONSTRAINT mail_queue_pkey PRIMARY KEY (id);


--
-- Name: mail_templates mail_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.mail_templates
    ADD CONSTRAINT mail_templates_pkey PRIMARY KEY (id);


--
-- Name: scheduler_run scheduler_run_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_run
    ADD CONSTRAINT scheduler_run_pkey PRIMARY KEY (id);


--
-- Name: scheduler_task_deps scheduler_task_deps_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_task_deps
    ADD CONSTRAINT scheduler_task_deps_pkey PRIMARY KEY (id);


--
-- Name: scheduler_task scheduler_task_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_task
    ADD CONSTRAINT scheduler_task_pkey PRIMARY KEY (id);


--
-- Name: scheduler_task scheduler_task_uuid_key; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_task
    ADD CONSTRAINT scheduler_task_uuid_key UNIQUE (uuid);


--
-- Name: scheduler_worker scheduler_worker_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_worker
    ADD CONSTRAINT scheduler_worker_pkey PRIMARY KEY (id);


--
-- Name: scheduler_worker scheduler_worker_worker_name_key; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_worker
    ADD CONSTRAINT scheduler_worker_worker_name_key UNIQUE (worker_name);


--
-- Name: t_articles t_articles_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles
    ADD CONSTRAINT t_articles_pkey PRIMARY KEY (id);


--
-- Name: t_comments t_comments_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_comments
    ADD CONSTRAINT t_comments_pkey PRIMARY KEY (id);


--
-- Name: t_distinct_words t_distinct_words_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_distinct_words
    ADD CONSTRAINT t_distinct_words_pkey PRIMARY KEY (id);


--
-- Name: t_distinct_words t_distinct_words_word_unique; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_distinct_words
    ADD CONSTRAINT t_distinct_words_word_unique UNIQUE (word);


--
-- Name: t_thematics t_keywords_list_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_thematics
    ADD CONSTRAINT t_keywords_list_pkey PRIMARY KEY (id);


--
-- Name: t_pdf t_pdf_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_pdf
    ADD CONSTRAINT t_pdf_pkey PRIMARY KEY (id);


--
-- Name: t_pdf t_pdf_recommendation_id_key; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_pdf
    ADD CONSTRAINT t_pdf_recommendation_id_key UNIQUE (recommendation_id);


--
-- Name: t_press_reviews t_press_review_contributors_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_press_reviews
    ADD CONSTRAINT t_press_review_contributors_pkey PRIMARY KEY (id);


--
-- Name: t_recommendations t_recommendations_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_recommendations
    ADD CONSTRAINT t_recommendations_pkey PRIMARY KEY (id);


--
-- Name: t_report_survey t_report_survey_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_report_survey
    ADD CONSTRAINT t_report_survey_pkey PRIMARY KEY (id);


--
-- Name: t_resources t_resources_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_resources
    ADD CONSTRAINT t_resources_pkey PRIMARY KEY (id);


--
-- Name: t_reviews t_reviewers_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_reviews
    ADD CONSTRAINT t_reviewers_pkey PRIMARY KEY (id);


--
-- Name: t_status_article t_status_article_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_status_article
    ADD CONSTRAINT t_status_article_pkey PRIMARY KEY (id);


--
-- Name: t_status_article t_status_article_status_key; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_status_article
    ADD CONSTRAINT t_status_article_status_key UNIQUE (status);


--
-- Name: t_suggested_recommenders t_suggested_recommenders_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_suggested_recommenders
    ADD CONSTRAINT t_suggested_recommenders_pkey PRIMARY KEY (id);


--
-- Name: t_supports t_supports_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_supports
    ADD CONSTRAINT t_supports_pkey PRIMARY KEY (id);


--
-- Name: t_articles_words tarticleswords_pkey; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles_words
    ADD CONSTRAINT tarticleswords_pkey PRIMARY KEY (distinct_word_id, article_id);


--
-- Name: t_press_reviews tpressreviewcontribs_unique; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_press_reviews
    ADD CONSTRAINT tpressreviewcontribs_unique UNIQUE (recommendation_id, contributor_id);


--
-- Name: t_suggested_recommenders tsuggestedrecommenders_unique; Type: CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_unique UNIQUE (article_id, suggested_recommender_id);


--
-- Name: help_idx; Type: INDEX; Schema: public; Owner: pci_admin
--

CREATE INDEX help_idx ON public.help_texts USING btree (hashtag, lang);


--
-- Name: t_articles_last_status_change_idx; Type: INDEX; Schema: public; Owner: pci_admin
--

CREATE INDEX t_articles_last_status_change_idx ON public.t_articles USING btree (last_status_change DESC NULLS LAST);


--
-- Name: t_distinct_words_word_idx; Type: INDEX; Schema: public; Owner: pci_admin
--

CREATE INDEX t_distinct_words_word_idx ON public.t_distinct_words USING btree (word);


--
-- Name: tdistinctwords_gist; Type: INDEX; Schema: public; Owner: pci_admin
--

CREATE INDEX tdistinctwords_gist ON public.t_distinct_words USING gist (word public.gist_trgm_ops);


--
-- Name: trecommendations_articleid_idx; Type: INDEX; Schema: public; Owner: pci_admin
--

CREATE INDEX trecommendations_articleid_idx ON public.t_recommendations USING btree (article_id);


--
-- Name: tuserwords_idx; Type: INDEX; Schema: public; Owner: pci_admin
--

CREATE INDEX tuserwords_idx ON public.t_user_words USING gist (word public.gist_trgm_ops);


--
-- Name: t_recommendations auto_last_change_trigger; Type: TRIGGER; Schema: public; Owner: pci_admin
--

CREATE TRIGGER auto_last_change_trigger BEFORE INSERT OR DELETE OR UPDATE OF recommendation_state ON public.t_recommendations FOR EACH ROW EXECUTE PROCEDURE public.auto_last_change_recommendation_trigger_function();


--
-- Name: t_reviews auto_last_change_trigger; Type: TRIGGER; Schema: public; Owner: pci_admin
--

CREATE TRIGGER auto_last_change_trigger BEFORE INSERT OR DELETE OR UPDATE OF review_state ON public.t_reviews FOR EACH ROW EXECUTE PROCEDURE public.auto_last_change_review_trigger_function();


--
-- Name: t_articles auto_last_status_change_trigger; Type: TRIGGER; Schema: public; Owner: pci_admin
--

CREATE TRIGGER auto_last_status_change_trigger BEFORE INSERT OR UPDATE OF status ON public.t_articles FOR EACH ROW EXECUTE PROCEDURE public.auto_last_status_change_trigger_function();


--
-- Name: t_recommendations auto_nb_recommendations_trigger; Type: TRIGGER; Schema: public; Owner: pci_admin
--

CREATE TRIGGER auto_nb_recommendations_trigger AFTER INSERT OR DELETE OR UPDATE ON public.t_recommendations FOR EACH ROW EXECUTE PROCEDURE public.auto_nb_recommendations_trigger_function();


--
-- Name: t_articles distinct_words_trigger; Type: TRIGGER; Schema: public; Owner: pci_admin
--

CREATE TRIGGER distinct_words_trigger AFTER INSERT OR UPDATE OF title, abstract, keywords, authors ON public.t_articles FOR EACH ROW EXECUTE PROCEDURE public.distinct_words_trigger_function();


--
-- Name: t_thematics propagate_field_deletion_trigger; Type: TRIGGER; Schema: public; Owner: pci_admin
--

CREATE TRIGGER propagate_field_deletion_trigger AFTER DELETE OR UPDATE OF keyword ON public.t_thematics FOR EACH ROW EXECUTE PROCEDURE public.propagate_field_deletion_function();


--
-- Name: auth_user user_words_trigger; Type: TRIGGER; Schema: public; Owner: pci_admin
--

CREATE TRIGGER user_words_trigger AFTER INSERT OR DELETE OR UPDATE OF first_name, last_name, city, country, laboratory, institution, thematics ON public.auth_user FOR EACH ROW EXECUTE PROCEDURE public.user_words_trigger_function();


--
-- Name: auth_cas auth_cas_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_cas
    ADD CONSTRAINT auth_cas_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_user(id) ON DELETE CASCADE;


--
-- Name: auth_event auth_event_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_event
    ADD CONSTRAINT auth_event_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_user(id) ON DELETE CASCADE;


--
-- Name: auth_membership auth_membership_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_membership
    ADD CONSTRAINT auth_membership_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.auth_group(id) ON DELETE CASCADE;


--
-- Name: auth_membership auth_membership_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_membership
    ADD CONSTRAINT auth_membership_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_user(id) ON DELETE CASCADE;


--
-- Name: auth_permission auth_permission_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.auth_permission
    ADD CONSTRAINT auth_permission_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.auth_group(id) ON DELETE CASCADE;


--
-- Name: mail_queue mail_queue_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.mail_queue
    ADD CONSTRAINT mail_queue_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.t_articles(id) ON DELETE CASCADE;


--
-- Name: mail_queue mail_queue_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.mail_queue
    ADD CONSTRAINT mail_queue_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES public.t_recommendations(id) ON DELETE CASCADE;


--
-- Name: mail_queue mail_queue_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.mail_queue
    ADD CONSTRAINT mail_queue_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_user(id) ON DELETE CASCADE;


--
-- Name: scheduler_run scheduler_run_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_run
    ADD CONSTRAINT scheduler_run_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.scheduler_task(id) ON DELETE CASCADE;


--
-- Name: scheduler_task_deps scheduler_task_deps_task_child_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.scheduler_task_deps
    ADD CONSTRAINT scheduler_task_deps_task_child_fkey FOREIGN KEY (task_child) REFERENCES public.scheduler_task(id) ON DELETE CASCADE;


--
-- Name: t_articles t_articles_art_stage_1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles
    ADD CONSTRAINT t_articles_art_stage_1_id_fkey FOREIGN KEY (art_stage_1_id) REFERENCES public.t_articles(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: t_articles t_articles_suggested_recommender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles
    ADD CONSTRAINT t_articles_suggested_recommender_id_fkey FOREIGN KEY (suggested_recommender_id) REFERENCES public.auth_user(id) ON DELETE RESTRICT;


--
-- Name: t_articles t_articles_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles
    ADD CONSTRAINT t_articles_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_user(id) ON DELETE SET NULL;


--
-- Name: t_comments t_comments_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_comments
    ADD CONSTRAINT t_comments_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_comments t_comments_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_comments
    ADD CONSTRAINT t_comments_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.t_comments(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_comments t_comments_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_comments
    ADD CONSTRAINT t_comments_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_user(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: t_pdf t_pdf_recommendation_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_pdf
    ADD CONSTRAINT t_pdf_recommendation_fkey FOREIGN KEY (recommendation_id) REFERENCES public.t_recommendations(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_press_reviews t_press_review_contributors_contributor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_press_reviews
    ADD CONSTRAINT t_press_review_contributors_contributor_id_fkey FOREIGN KEY (contributor_id) REFERENCES public.auth_user(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: t_recommendations t_recommendations_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_recommendations
    ADD CONSTRAINT t_recommendations_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.t_articles(id) ON DELETE CASCADE;


--
-- Name: t_recommendations t_recommendations_recommender_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_recommendations
    ADD CONSTRAINT t_recommendations_recommender_id_fkey FOREIGN KEY (recommender_id) REFERENCES public.auth_user(id) ON DELETE SET NULL;


--
-- Name: t_reviews t_reviewers_recommendation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_reviews
    ADD CONSTRAINT t_reviewers_recommendation_id_fkey FOREIGN KEY (recommendation_id) REFERENCES public.t_recommendations(id) ON DELETE CASCADE;


--
-- Name: t_reviews t_reviewers_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_reviews
    ADD CONSTRAINT t_reviewers_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.auth_user(id) ON DELETE SET NULL;


--
-- Name: t_articles tarticles_status_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles
    ADD CONSTRAINT tarticles_status_fkey FOREIGN KEY (status) REFERENCES public.t_status_article(status);


--
-- Name: t_articles_words tarticleswords_tarticles_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles_words
    ADD CONSTRAINT tarticleswords_tarticles_fkey FOREIGN KEY (article_id) REFERENCES public.t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_articles_words tarticleswords_tdistinctwords_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_articles_words
    ADD CONSTRAINT tarticleswords_tdistinctwords_fkey FOREIGN KEY (distinct_word_id) REFERENCES public.t_distinct_words(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_press_reviews tpressreview_trecommendation_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_press_reviews
    ADD CONSTRAINT tpressreview_trecommendation_fkey FOREIGN KEY (recommendation_id) REFERENCES public.t_recommendations(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_report_survey treportsurvey_tarticles_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_report_survey
    ADD CONSTRAINT treportsurvey_tarticles_fkey FOREIGN KEY (article_id) REFERENCES public.t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_report_survey treportsurvey_tarticles_stage1_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_report_survey
    ADD CONSTRAINT treportsurvey_tarticles_stage1_fkey FOREIGN KEY (temp_art_stage_1_id) REFERENCES public.t_articles(id) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- Name: t_suggested_recommenders tsuggestedrecommenders_authusers_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_authusers_fkey FOREIGN KEY (suggested_recommender_id) REFERENCES public.auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_suggested_recommenders tsuggestedrecommenders_tarticles_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_suggested_recommenders
    ADD CONSTRAINT tsuggestedrecommenders_tarticles_fkey FOREIGN KEY (article_id) REFERENCES public.t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- Name: t_user_words tuserwords_authuser_fkey; Type: FK CONSTRAINT; Schema: public; Owner: pci_admin
--

ALTER TABLE ONLY public.t_user_words
    ADD CONSTRAINT tuserwords_authuser_fkey FOREIGN KEY (id) REFERENCES public.auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

SET search_path to public;

-- 2022-02-21 updates/alter_new_submission_fields.sql

ALTER TABLE "t_articles" 
DROP COLUMN IF EXISTS no_results_based_on_data,
DROP COLUMN IF EXISTS no_codes_used_in_study,
DROP COLUMN IF EXISTS no_scripts_used_for_result,
ALTER COLUMN  results_based_on_data TYPE character varying(512),
ALTER COLUMN  scripts_used_for_result TYPE character varying(512),
ALTER COLUMN  codes_used_in_study TYPE character varying(512),
ALTER COLUMN  results_based_on_data DROP DEFAULT,
ALTER COLUMN  scripts_used_for_result DROP DEFAULT,
ALTER COLUMN  codes_used_in_study DROP DEFAULT;


-- 2022-02-18 updates/add_new_field_to_reviews.sql

CREATE TYPE duration AS ENUM('Two weeks', 'Three weeks', 'Four weeks', 'Five weeks', 'Six weeks', 'Seven weeks', 'Eight weeks');

ALTER TABLE "t_reviews"
ADD COLUMN  IF NOT EXISTS review_duration duration DEFAULT 'Three weeks';

-- 2022-03-03 updates/add_new_field_mail_queue.sql

ALTER TABLE "mail_queue"
ADD COLUMN  IF NOT EXISTS review_id integer;

-- 2022-03-15 updates/add_new_article_field.sql

ALTER TABLE "t_articles"
ADD COLUMN  IF NOT EXISTS suggest_reviewers text;

-- 2022-03-15 updates/set-default-newsletter-weekly.sql

ALTER TABLE auth_user
ALTER alerts SET DEFAULT 'Weekly';

-- 2022-03-31 updates/add_competitors.sql

ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS competitors text;

-- 2022-03-30 updates/add_anonymous_agreement.sql

ALTER TABLE "t_reviews"
ADD COLUMN anonymous_agreement boolean;

-- 2022-04-22 updates/add_5_working_days_duration.sql
ALTER TYPE duration ADD VALUE 'Five working days';

-- 2022-04-28 updates/t_articles_new_field.sql

ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS doi_of_published_article character varying(512);

-- 2022-05-24 updates/new_recomm_article_field.sql

ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  submitter_details character varying(512);

ALTER TABLE "t_recommendations"
ADD COLUMN IF NOT EXISTS  recommender_details character varying(512);

ALTER TABLE "t_press_reviews"
ADD COLUMN IF NOT EXISTS  contributor_details character varying(512);

-- 2022-06-16 updates/alter_data_scripts.sql
ALTER TABLE "t_articles"
ALTER COLUMN  data_doi TYPE text,
ALTER COLUMN  scripts_doi TYPE text,
ALTER COLUMN  codes_doi TYPE text;

-- 2022-08-26 updates/new_t_article_field.sql
ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS request_submission_change boolean DEFAULT false;

-- updates/new_table.sql
CREATE TABLE submissions (
    id serial PRIMARY KEY,
    allow_submissions boolean DEFAULT true
);

ALTER TABLE public.submissions OWNER TO pci_admin;

-- updates/insert_into_submissions.sql
INSERT INTO submissions("allow_submissions")
VALUES
(true);

-- 2022-09-29 updates/new_table.sql
CREATE TABLE t_excluded_recommenders (
    id serial PRIMARY KEY,
    article_id integer,
    excluded_recommender_id integer,
    CONSTRAINT texcludedrecommenders_authusers_fkey FOREIGN KEY (excluded_recommender_id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT texcludedrecommenders_tarticles_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE
);

ALTER TABLE public.t_excluded_recommenders OWNER TO pci_admin;

-- 2022-10-11 updates/validation_fields.sql
ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS validation_timestamp timestamp without time zone;

ALTER TABLE "t_recommendations"
ADD COLUMN IF NOT EXISTS validation_timestamp timestamp without time zone;

-- 2022-10-27 updates/add_bcc_to_mailqueue.sql
ALTER TABLE mail_queue ADD COLUMN bcc_mail_addresses text;

-- 2022-11-30 updates/new_t_article_field.sql
ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  preprint_server character varying(512);

-- 2023-01-02 updates/fundings.sql
ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS  funding character varying(1024) DEFAULT '';

-- 2023-01-04 updates/update_configuration_table.sql
alter table submissions rename to config;
alter table config add column issn text;

-- 2023-01-20 updates/add_allowed_filetypes_config.sql
alter table config add column allowed_upload_filetypes text;

-- 2023-01-25 updates/refactor_v_article_recommender.sql
DROP VIEW v_article_recommender;
CREATE OR REPLACE VIEW v_article_recommender AS
SELECT
	r.article_id AS id,
	r.id AS recommendation_id,
	(au.first_name || ' ' || au.last_name) AS recommender
FROM (
	t_recommendations r
	LEFT JOIN auth_user au ON (r.recommender_id = au.id)
)
WHERE r.id in (select max(id) from t_recommendations group by article_id)
;

CREATE OR REPLACE VIEW v_article AS
SELECT
	a.*,
	r.recommender,
	rev.reviewers,
	to_char(a.upload_timestamp, 'YYYY-MM-DD HH24:MI:SS') as submission_date
FROM
	t_articles a
	JOIN v_article_recommender r ON a.id = r.id
	JOIN v_reviewers rev ON rev.id = r.recommendation_id
;

alter view v_article owner to pci_admin;
alter view v_article_recommender owner to pci_admin;

-- 2023-03-01 updates/add_article_year.sql
ALTER TABLE "t_articles"
ADD COLUMN IF NOT EXISTS article_year integer;

-- 2023-03-06 updates/tracked_changes.sql
ALTER TABLE "t_report_survey"
ADD COLUMN IF NOT EXISTS  tracked_changes_url character varying(512) DEFAULT '';

ALTER TABLE "t_report_survey" 
RENAME COLUMN "q30" TO "q30_details";

ALTER TABLE "t_report_survey"
ADD COLUMN IF NOT EXISTS  q30 character varying(512) DEFAULT '';

-- templates updates => sql_dumps/insert_default_mail_templates_pci_RR.sql

-- 2023-03-07 updates/manager_views.sql
CREATE OR REPLACE VIEW v_postprint_recommendations AS
SELECT 
    r.id AS id, 
    r.last_change, 
    r.article_id, 
    r.doi, 
    r.is_closed, 
    r.recommendation_state, 
    r.recommender_id, 
    r.recommendation_timestamp, 
    r.recommendation_comments, 
    r.recommender_details,
    a.already_published, 
    a.status, 
    a.report_stage,
    a.art_stage_1_id, 
    a.scheduled_submission_date
FROM 
    t_recommendations r,
    t_articles a 
WHERE 
    r.article_id = a.id 
AND a.already_published=true
AND r.id in (select max(id) from t_recommendations group by article_id)
;

CREATE OR REPLACE VIEW v_preprint_recommendations AS
SELECT 
    r.id AS id, 
    r.last_change, 
    r.article_id, 
    r.doi, 
    r.is_closed, 
    r.recommendation_state, 
    r.recommender_id, 
    r.recommendation_timestamp, 
    r.recommendation_comments, 
    r.recommender_details,
    a.already_published, 
    a.status, 
    a.report_stage,
    a.art_stage_1_id, 
    a.scheduled_submission_date
FROM 
    t_recommendations r,
    t_articles a 
WHERE 
    r.article_id = a.id 
AND a.already_published=false
AND a.status IN ('Under consideration', 'Scheduled submission under consideration')
AND r.id in (select max(id) from t_recommendations group by article_id)
;

alter view v_preprint_recommendations owner to pci_admin;
alter view v_postprint_recommendations owner to pci_admin;
