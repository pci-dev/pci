delete from mail_templates where hashtag in (
	'#SubmitterPreprintSubmitted',
	'#SubmitterPreprintSubmittedStage1',
	'#SubmitterPreprintSubmittedStage2',
	'#SubmitterPreprintSubmittedStage1ScheduledSubmission'
);

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#SubmitterPreprintSubmitted','default','{{appName}}: Your submission','Mail to submitter to indicate the validation of their submission','<p>Dear {{destPerson}},<br><br>We have validated your submission to {{longname}}.</p>
<div>We have sent a message to all recommenders of {{appName}} you may have suggested to let them know about this submission. You will be notified by e-mail if a recommender decides to start the peer-review process for your preprint. If none of them decide to act as a recommender, you''ll receive an e-mail inviting you to suggest additionnal recommenders (we can also make suggestions if you wish).&nbsp;</div>
<div><br>We remind you that this preprint must not be published or submitted for publication elsewhere. If this preprint is taken in charge by a recommender and therefore sent out for review, you must not submit it to a journal until the evaluation process is complete (ie until it has been rejected or recommended by {{appName}}).</div>
<div>&nbsp;</div>
<div>To view or cancel your submission, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or logging onto the {{appName}} website and go to ''For contributors —&gt; Your submitted preprints'' in the top menu. As long as a recommender has not picked up your submitted article, you can also suggest additional recommenders.</div>
<div>&nbsp;</div>
<div>Note that 8 automated translations were generated in Chinese (Mandarin), Hindi, Spanish, French, Arabic, Portuguese, Russian, and Japanese. You have the possibility to edit and correct these translations. You also have the possibility to add your own translations in 2 languages of your choice. To do so, follow this link: <a href="{{editTranslationLink}}">{{editTranslationLink}}</a><br><br>We thank you again for your submission.<br><br>Yours sincerely,<br><br>The Managing Board of {{appName}}</div>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#SubmitterPreprintSubmittedStage1','default','{{appName}}: Your submission','Mail to submitter to indicate the validation of their submission','<p>Dear {{destPerson}},</p>
<p>Thank you for submitting your Stage 1 manuscript to {{appName}}. Your submission has now been validated by the Managing Board and recommenders have been invited to take the assignment. You will be notified by email when a recommender agrees to handle your submission. If none of the invited recommenders is able to act as a recommender, you may receive an email inviting you to suggest additional recommenders.&nbsp;</p>
<p>We remind you that this report must not be published or submitted for publication elsewhere. If this report is taken on by a recommender, and therefore sent out for review, you must not submit it to a journal until the evaluation process is complete (i.e., until it has been rejected or received its Stage 2 recommendation by {{appName}}).</p>
<p>To view or cancel your submission, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or log into the {{appName}} website and go to ''For contributors —&gt; Your submitted reports'' in the top menu. You can also monitor the progress of your submission any time by navigating to ''For contributors'' &gt; ''Your submitted reports'' &gt; ''VIEW/EDIT'' &gt; and then scroll down and expand the Timeline section.&nbsp;</p>
<p>Note that 8 automated translations were generated in Chinese (Mandarin), Hindi, Spanish, French, Arabic, Portuguese, Russian, and Japanese. You have the possibility to edit and correct these translations. You also have the possibility to add your own translations in 2 languages of your choice. To do so, follow this link: <a href="{{editTranslationLink}}">{{editTranslationLink}}</a></p>
<p>We thank you again for your submission.</p>
<p>Yours sincerely,</p>
<p>The Managing Board of {{appName}}</p>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#SubmitterPreprintSubmittedStage2','default','{{appName}}: Your submission','Mail to submitter to indicate the validation of their submission','<p>Dear {{destPerson}},</p>
<p>We have validated your submission to ({{appName}}).</p>
<p>We have sent a message to all recommenders of {{appName}} you may have suggested to let them know about this submission. You will be notified by e-mail if a recommender decides to start the peer-review process for your report. If none of them decide to act as a recommender, you''ll receive an e-mail inviting you to suggest additional recommenders (we can also make suggestions if you wish).&nbsp;</p>
<p>We remind you that this report must not be published or submitted for publication elsewhere. If this report is taken on by a recommender, and therefore sent out for review, you must not submit it to a journal until the evaluation process is complete (i.e., until it has been rejected or recommended by {{appName}}).</p>
<p>&nbsp;</p>
<p>To view or cancel your submission, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or log into the {{appName}} website and go to ''For contributors —&gt; Your submitted reports'' in the top menu. As long as a recommender has not picked up your submitted article, you can also suggest additional recommenders.</p>
<p>Note that 8 automated translations were generated in Chinese (Mandarin), Hindi, Spanish, French, Arabic, Portuguese, Russian, and Japanese. You have the possibility to edit and correct these translations. You also have the possibility to add your own translations in 2 languages of your choice. To do so, follow this link: <a href="{{editTranslationLink}}">{{editTranslationLink}}</a></p>
<p>We thank you again for your submission.</p>
<p>Yours sincerely,</p>
<p>The Managing Board of {{appName}}</p>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#SubmitterPreprintSubmittedStage1ScheduledSubmission','default','{{appName}}: Your submission','Mail to submitter to indicate the validation of their Stage 1 snapshot','<p>Dear {{destPerson}},</p>
<p>Thank you for submitting your Stage 1 snapshot to {{appName}} for consideration via the Scheduled Review track. Your submission has now been validated by the Managing Board and recommenders have been invited to take the assignment. You will be notified by email when a recommender agrees to handle your submission. If none of the invited recommenders is able to act as a recommender, you may receive an email inviting you to suggest additional recommenders.&nbsp;</p>
<p>To view or cancel your submission, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or log into the {{appName}} website and go to ''For contributors —&gt; Your submitted reports'' in the top menu.</p>
<p>Note that 8 automated translations were generated in Chinese (Mandarin), Hindi, Spanish, French, Arabic, Portuguese, Russian, and Japanese. You have the possibility to edit and correct these translations. You also have the possibility to add your own translations in 2 languages of your choice. To do so, follow this link: <a href="{{editTranslationLink}}">{{editTranslationLink}}</a></p>
<p>We thank you again for your submission.</p>
<p>Yours sincerely,</p>
<p>The Managing Board of {{appName}}</p>');
