delete from mail_templates where hashtag in (
	'#ReminderUserCompleteSubmissionCOAR',
	'#ReminderSubmitterRevisedVersionWarningCOAR',
	'#ReminderSubmitterRevisedVersionNeededCOAR'
);
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
