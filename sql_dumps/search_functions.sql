CREATE OR REPLACE FUNCTION public.user_words_trigger_function() RETURNS trigger
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
