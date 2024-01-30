delete from mail_templates where hashtag in (
	'#SubmitterPreprintSubmitted'
);

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#SubmitterPreprintSubmitted','default','{{appName}}: Your submission','Mail to submitter to indicate the validation of their submission','<p>Dear {{destPerson}},<br><br>We have validated your submission to {{longname}}.</p>
<div>We have sent a message to all recommenders of {{appName}} you may have suggested to let them know about this submission. You will be notified by e-mail if a recommender decides to start the peer-review process for your preprint. If none of them decide to act as a recommender, you''ll receive an e-mail inviting you to suggest additionnal recommenders (we can also make suggestions if you wish).&nbsp;</div>
<div><br>We remind you that this preprint must not be published or submitted for publication elsewhere. If this preprint is taken in charge by a recommender and therefore sent out for review, you must not submit it to a journal until the evaluation process is complete (ie until it has been rejected or recommended by {{appName}}).</div>
<div>&nbsp;</div>
<div>To view or cancel your submission, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or logging onto the {{appName}} website and go to ''For contributors —&gt; Your submitted preprints'' in the top menu. As long as a recommender has not picked up your submitted article, you can also suggest additional recommenders.</div>
<div>&nbsp;</div>
<div>Note that 5 automated translations were generated in Chinese (Mandarin), Hindi, Spanish, French, Arabic. You have the possibility to edit and correct these translations. You also have the possibility to add your own translations in 2 languages of your choice. To do so, follow this link: <a href="{{editTranslationLink}}">{{editTranslationLink}}</a><br><br>We thank you again for your submission.<br><br>Yours sincerely,<br><br>The Managing Board of {{appName}}</div>');
