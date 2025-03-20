alter table t_suggested_recommenders add column if not exists recommender_validated bool;

INSERT INTO public.mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#ValidSuggestedRecommender','default','{{appName}}: New suggested recommenders pending validation','New suggested recommenders pending validation','<div>Dear members of the Managing Board,</div>
<div><br>{{submitterPerson}} has suggested one or more other recommenders to handle their submitted preprint entitled {{articleTitle}}.</div>
<div><br>Please follow this link {{linkTarget}} or click the buttons below to validate or not these suggested recommenders.</div>
<div><br>Thanks in advance.</div>
<div>Have a nice day!</div>');

INSERT INTO public.mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#ReminderValidSuggestedRecommender','default','{{appName}}: URGENT action required - Validate new suggested recommenders','Validate new suggested recommenders','<div>Dear members of the Managing Board,</div>
<div><br>As a reminder, {{submitterPerson}} has suggested one or more other recommenders to handle their submitted preprint entitled {{articleTitle}}.</div>
<div><br>Please follow this link {{linkTarget}} or click the buttons below to validate or not these suggested recommenders.</div>
<div><br>Thanks in advance.<br>Have a nice day!</div>');
