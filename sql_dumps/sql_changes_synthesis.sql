ALTER TABLE public.t_articles DISABLE TRIGGER auto_last_status_change_trigger;
ALTER TABLE public.t_articles DISABLE TRIGGER distinct_words_trigger;

ALTER TABLE public.t_articles ADD COLUMN IF NOT EXISTS "is_searching_reviewers" boolean DEFAULT false;
ALTER TABLE public.t_articles ADD COLUMN IF NOT EXISTS "report_stage" VARCHAR(128);
ALTER TABLE public.t_articles ADD COLUMN IF NOT EXISTS "scheduled_submission_date" date;
ALTER TABLE public.t_articles ADD COLUMN IF NOT EXISTS "art_stage_1_id" integer;
ALTER TABLE public.t_articles ADD COLUMN IF NOT EXISTS "sub_thematics" VARCHAR(128);
ALTER TABLE public.t_articles ADD COLUMN IF NOT EXISTS "record_url_version" VARCHAR(128);
ALTER TABLE public.t_articles ADD COLUMN IF NOT EXISTS "record_id_version" VARCHAR(128);

ALTER TABLE public.t_articles DROP CONSTRAINT IF EXISTS t_articles_art_stage_1_id_fkey;
ALTER TABLE public.t_articles ADD CONSTRAINT t_articles_art_stage_1_id_fkey FOREIGN KEY (art_stage_1_id) REFERENCES public.t_articles (id) MATCH SIMPLE ON UPDATE CASCADE ON DELETE SET NULL;

ALTER TABLE public.t_articles ENABLE TRIGGER auto_last_status_change_trigger;
ALTER TABLE public.t_articles ENABLE TRIGGER distinct_words_trigger;


CREATE TABLE IF NOT EXISTS "t_report_survey" (
    "id" SERIAL PRIMARY KEY,
    "article_id" INTEGER,
    "q1" VARCHAR(1024),
    "q2" VARCHAR(1024),
    "q3" VARCHAR(1024),
    "q4" BOOLEAN,
    "q5" TEXT,
    "q6" VARCHAR(1024),
    "q7" VARCHAR(1024),
    "q8" VARCHAR(1024),
    "q9" VARCHAR(1024),
    "q10" DATE,
    "q11" VARCHAR(128),
    "q11_details" TEXT,
    "q12" VARCHAR(128),
    "q12_details" TEXT,
    "q13" VARCHAR(512),
    "q13_details" TEXT,
    "q14" BOOLEAN,
    "q15" TEXT,
    "q16" VARCHAR(128),
    "q17" VARCHAR(128),
    "q18" BOOLEAN,
    "q19" BOOLEAN,
    "q20" VARCHAR(128),
    "q21" VARCHAR(128),
    "q22" VARCHAR(128),
    "q23" VARCHAR(128),
    "q24" DATE,
    "q24_1" VARCHAR(128),
    "q24_1_details" TEXT,
    "q25" BOOLEAN,
    "q26" VARCHAR(512),
    "q26_details" TEXT,
    "q27" VARCHAR(512),
    "q27_details" TEXT,
    "q28" VARCHAR(512),
    "q28_details" TEXT,
    "q29" BOOLEAN,
    "q30" VARCHAR(256),
    "q31" VARCHAR(128),
    "temp_art_stage_1_id" integer
);

ALTER TABLE "t_report_survey" DROP CONSTRAINT IF EXISTS treportsurvey_tarticles_fkey;
ALTER TABLE "t_report_survey" DROP CONSTRAINT IF EXISTS t_report_survey_article_id_fkey;
ALTER TABLE "t_report_survey" ADD CONSTRAINT treportsurvey_tarticles_fkey FOREIGN KEY ("article_id") REFERENCES public.t_articles("id") ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE "t_report_survey" DROP CONSTRAINT IF EXISTS t_report_survey_temp_art_stage_1_id_fkey;
ALTER TABLE "t_report_survey" DROP CONSTRAINT IF EXISTS treportsurvey_tarticles_stage1_fkey;
ALTER TABLE "t_report_survey" ADD CONSTRAINT treportsurvey_tarticles_stage1_fkey FOREIGN KEY ("temp_art_stage_1_id") REFERENCES public.t_articles("id") ON UPDATE CASCADE ON DELETE SET NULL;
--  REFERENCES public.t_articles ("id") ON DELETE CASCADE
 
ALTER TABLE "auth_user" ADD COLUMN IF NOT EXISTS "recover_email" character varying(512);
ALTER TABLE "auth_user" ADD COLUMN IF NOT EXISTS "recover_email_key" character varying(512);
ALTER TABLE "auth_user" DROP CONSTRAINT IF EXISTS auth_user_recover_email_key;
ALTER TABLE "auth_user" ADD CONSTRAINT auth_user_recover_email_key UNIQUE ("recover_email");
ALTER TABLE "auth_user" DROP CONSTRAINT IF EXISTS auth_user_recover_email_key_key;
ALTER TABLE "auth_user" ADD CONSTRAINT auth_user_recover_email_key_key UNIQUE ("recover_email_key");

UPDATE auth_user SET alerts='Weekly' WHERE alerts != '||' AND alerts LIKE '%||%';
UPDATE auth_user SET alerts='Never' WHERE alerts = '||';

UPDATE auth_group SET role = 'developer' WHERE role = 'developper';

CREATE TABLE IF NOT EXISTS "mail_queue" (
    "id" SERIAL PRIMARY KEY,
    "removed_from_queue" BOOLEAN DEFAULT false,
    "sending_status" VARCHAR(128),
    "sending_attempts" INTEGER,
    "sending_date" TIMESTAMP,
    "dest_mail_address" VARCHAR(256),
    "cc_mail_addresses" VARCHAR(1024),
    "user_id" INTEGER REFERENCES "auth_user" ("id") ON DELETE CASCADE,
    "article_id" INTEGER REFERENCES public.t_articles ("id") ON DELETE CASCADE,
    "recommendation_id" INTEGER REFERENCES "t_recommendations" ("id") ON DELETE CASCADE,
    "mail_subject" VARCHAR(256),
    "mail_content" TEXT,
    "mail_template_hashtag" VARCHAR(128),
    "reminder_count" INTEGER
);


CREATE TABLE IF NOT EXISTS "mail_templates"(
    "id" SERIAL PRIMARY KEY,
    "hashtag" VARCHAR(128),
    "lang" VARCHAR(10),
    "subject" VARCHAR(256),
    "description" VARCHAR(512),
    "contents" TEXT
);


ALTER TABLE t_reviews DISABLE TRIGGER auto_last_change_trigger;
UPDATE t_reviews SET review_state = 'Review completed' WHERE review_state = 'Completed';
UPDATE t_reviews SET review_state = 'Willing to review' WHERE review_state = 'Ask to review';
UPDATE t_reviews SET review_state = 'Awaiting review' WHERE review_state = 'Under consideration';
UPDATE t_reviews SET review_state = 'Awaiting response' WHERE review_state = 'Pending';
ALTER TABLE t_reviews ENABLE TRIGGER auto_last_change_trigger;


CREATE OR REPLACE FUNCTION public.search_articles_new(mythematics text[], mywords text[], mystatus character varying DEFAULT '''Recommended''::character varying', mylimit real DEFAULT '0.4', all_by_default boolean DEFAULT 'false')
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




