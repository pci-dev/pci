CREATE TABLE tweets(
	id serial4 PRIMARY KEY,
	post_id bigint UNIQUE NOT NULL,
	text_content text NOT NULL,
	thread_position int NOT NULL,
	article_id integer NOT NULL REFERENCES t_articles(id) ON DELETE CASCADE,
	recommendation_id integer NOT NULL REFERENCES t_recommendations(id) ON DELETE CASCADE,
	parent_id integer REFERENCES tweets(id) ON DELETE CASCADE
);
