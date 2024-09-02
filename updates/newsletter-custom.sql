delete from mail_templates where hashtag in (
	'#MailSubscribers'
);

INSERT INTO public.mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#MailSubscribers','default','{{subject}}','Mail subscribers','{{content}}');


delete from help_texts where hashtag in (
	'#SendMailSubscribersTitle',
	'SendMailSubscribersText'
);

INSERT INTO help_texts (hashtag,lang,contents) VALUES ('#SendMailSubscribersTitle','default','Send mail to all subscribers');
INSERT INTO help_texts (hashtag,lang,contents) VALUES ('#SendMailSubscribersText','default','Send a general newsletter to all users that subscribe to the newsletter in their profile.');
