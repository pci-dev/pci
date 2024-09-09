delete from help_texts where hashtag in (
	'#SendMailSubscribersText'
);

INSERT INTO help_texts (hashtag,lang,contents) VALUES ('#SendMailSubscribersText','default','Send a general newsletter to all users that subscribed to the newsletter in their profile.');
