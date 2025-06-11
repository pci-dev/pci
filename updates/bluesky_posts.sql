CREATE TABLE bluesky_posts(
	id serial4 PRIMARY KEY,
	post_id varchar(100) UNIQUE NOT NULL,
	text_content text NOT NULL,
	thread_position int NOT NULL,
	article_id integer NOT NULL REFERENCES t_articles(id) ON DELETE CASCADE,
	recommendation_id integer NOT NULL REFERENCES t_recommendations(id) ON DELETE CASCADE,
	parent_id integer REFERENCES bluesky_posts(id) ON DELETE CASCADE
);

ALTER TABLE bluesky_posts OWNER TO pci_admin;
