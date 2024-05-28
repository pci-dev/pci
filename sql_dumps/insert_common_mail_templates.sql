-- updates/submitterPreprintSubmitted.sql
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

-- updates/add_template_ResetPassword.sql
delete from mail_templates where hashtag = '#UserResetPassword';
insert into mail_templates
(hashtag, description, lang, subject, contents) values (
'#UserResetPassword',
'Mail to user to reset their password',
'default',
'{{appName}}: Reset password',
'<p>You requested to reset your password. Please click the following link: <a href="{{linkTarget}}">reset password</a>.</p><br><p>Thank you for your time and support.</p>'
);

-- updates/update_UserCompleteSubmissionCOAR.sql
delete from mail_templates where hashtag = '#UserCompleteSubmissionCOAR';
insert into mail_templates
(hashtag, description, lang, subject, contents) values (
'#UserCompleteSubmissionCOAR',
'Mail to submitter when submission made from a preprint server',
'default',
'{{appName}}: Please complete your submission made from a preprint server',
'<p>Dear {{destPerson}}</p><p>Thank you for your submission made via a preprint server and sent to {{appName}}.</p><p>We have just created an account for you, so you can proceed with the submission.</p><p>Welcome on board!</p><p dir="auto">Before completing the submission process, please carefully check the following points:</p><p dir="auto">- {{appName}} is a preprint reviewing service and not a journal,<br>- If positively evaluated by {{appName}}, your preprint will be publicly recommended and you could then transfer it for publication in the Peer Community Journal or submit it to a PCI-friendly journal,<br>- If your preprint contains data, scripts (e.g. for statistical analysis, like R scripts) and/or codes (e.g. codes for original programs or software), they should be made available to reviewers at submission. Data, scripts or codes must be carefully described such that another researcher can reuse them. If your preprint is eventually recommended, data and script should be made available to the readers either in the text or through a correctly versioned deposit in an open repository with a DOI or another permanent identifier (such as a SWHID of <a href="https://www.softwareheritage.org/" target="_blank">Software Heritage</a>).</p><ul><li>Your preprint must not be published or under consideration for evaluation elsewhere at the time of its submission to {{appName}}. If your preprint is sent out for review by {{appName}}, you are not permitted to submit it to a journal until the {{appName}} evaluation process has been completed. You cannot, therefore, submit your preprint to a journal before its rejection or recommendation by {{appName}},</li><li>You and your co-authors should have no financial conflict of interest (see a definition <a href="{{aboutEthicsLink}}">here</a>) relating to the articles you submit. If you are unsure whether your article may be associated with financial conflicts of interest, please send an Email to <a href="mailto:contact@peercommunityin.org">contact@peercommunityin.org</a> to ask for clarification.</li></ul><p dir="auto">Please note that:</p><ul><li>It can take up to 20 days before a recommender decides to handle your preprint and therefore to send it out for peer-review.</li><li>The median time between submission and the recommender''s decision based on the first round of peer-review is currently 50 days.</li><li>The evaluation of your preprint might take several rounds of review before the recommender take the final decision to reject or recommend your preprint.</li><li>Details about the evaluation &amp; recommendation process can be found <a href="{{helpGenericLink}}">here</a>.</li></ul><p>Please click on one of the buttons below.<br>Thanks again for your submission.<br>The Managing Board of {{appName}}</p>
<hr style="border-top: 1px solid #dddddd; margin: 15px 0px;">
<div style="width: 100%; text-align: center; margin-bottom: 25px;"><a href="{{completeSubmissionLink}}" style="text-decoration: none; display: block"><span style="margin: 10px; font-size: 14px; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: block; hyphens: none;background: #93c54b">Complete your submission</span></a><b>OR</b><a href="{{cancelSubmissionLink}}" style="text-decoration: none; display: block"><span style="margin: 10px; font-size: 14px; font-weight:bold; color: white; padding: 5px 15px; border-radius: 5px; display: block; hyphens: none;background: #f47c3c">Cancel your submission</span></a></div>'
);

-- updates/unsubscription_mail_template.sql
INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#UnsubscriptionAlert','default','Unsubscription','Unsubscription','<p><span class="HwtZe" lang="en"><span class="jCAhz ChMk0b"><span class="ryNqvb">User {{person}} [{{address}}] has unsubscribed from {{appLongName}}.</span></span></span></p>');

-- updates/add_ReminderSubmitterRevisedVersion...COAR.sql
insert into mail_templates
(hashtag, description, lang, subject, contents) values (
'#ReminderSubmitterRevisedVersionWarningCOAR',
'Mail to submitter to have some news about their revised version',
'default',
'{{appName}}: Revised version - reminder',
'<p>Dear {{destPerson}},</p>
<p>Thanks again for submitting your preprint to {{appName}}, we really appreciate it.</p>
<p>You should have received the decision of the recommender and the reviews on which they based their decision. We hope you found this feedback interesting and constructive. We are now waiting for your revised version, which we expect to receive within 2 months. If you need more time, just tell us.</p>
<p>As a kind reminder, please find below the email we originally sent you.</p>
<hr>
{{message}}
'
);
insert into mail_templates
(hashtag, description, lang, subject, contents) values (
'#ReminderSubmitterRevisedVersionNeededCOAR',
'Mail to submitter to verify that they received the decision and if they intend to resubmit',
'default',
'{{appName}}: Revised version?',
'<p>Dear {{destPerson}},</p>
<p>Following-up on the preprint you submitted to {{appName}}, I was wondering whether you found the time to revise the manuscript. There is no rush on our side, however we were expecting a revised version within 2 months. Should you need more time, just let us know of an approximate completion date and we will adjust a possible reminder accordingly.</p>
<p>Please find below the email we originally sent you.</p>
<hr>
{{message}}
'
);
insert into mail_templates
(hashtag, description, lang, subject, contents) values (
'#ReminderUserCompleteSubmissionCOAR',
'Mail to submitter to remind them to complete their submission',
'default',
'{{appName}}: Complete your submission - reminder',
'<p>Dear {{destPerson}}</p>
<p>Thanks for submitting the preprint "{{articleTitle}}"  via a preprint server to {{appName}}.</p>
<p>This is a kind reminder for you to complete your submission.</p>
<p>Please find below the email we originally sent you.</p>
<hr>
{{message}}
'
);

--- 2024-05-27 updates/BiorxivFTPAlert_template.sql
INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#BiorxivFTPAlert','default','Biorvix FTP Alert','Biorvix FTP Alert','<p>Pre-submission from bioRxiv received on our FTP.</p>
<p>Content:</p>
<p>{{xmlContent}}</p>
<p>&nbsp;</p>');
