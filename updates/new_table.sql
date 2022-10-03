CREATE TABLE t_excluded_recommenders (
    id serial PRIMARY KEY,
    article_id integer,
    excluded_recommender_id integer,
    CONSTRAINT texcludedrecommenders_authusers_fkey FOREIGN KEY (excluded_recommender_id) REFERENCES auth_user(id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT texcludedrecommenders_tarticles_fkey FOREIGN KEY (article_id) REFERENCES t_articles(id) ON UPDATE CASCADE ON DELETE CASCADE
);
