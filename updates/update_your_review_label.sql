delete from help_texts where hashtag in (
	'#UserMyReviewsTitle'
);

INSERT INTO help_texts (hashtag,lang,contents) VALUES ('#UserMyReviewsTitle','default','<p>Your past and ongoing reviews</p>');
