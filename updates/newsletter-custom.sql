delete from mail_templates where hashtag in (
	'#MailSubscribers'
);

INSERT INTO public.mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#MailSubscribers','default','{{subject}}','Mail subscribers','{{content}}');
