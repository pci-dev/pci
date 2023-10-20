delete from mail_templates where hashtag in (
	'#UserResetPassword',
	'#UserCompleteSubmission'
);
INSERT INTO mail_templates (hashtag, lang, subject, description, contents)
VALUES
(
E'#UserCompleteSubmissionCOAR',
E'default',
E'{{appName}}: Please complete your submission made from a preprint server',
E'Mail to submitter when submission made from a preprint server',
E'<p>Dear {{destPerson}}</p><p>Thank you for your submission made via a preprint server and sent to {{appName}}.</p><p>We have just created an account for you, so you can proceed with the submission.</p><p>Welcome on board!</p><p>Please click on the following link: <a href="{{linkTarget}}">Complete your submission</a></p><p>and complete your submission as follows:</p><ol><li>Complete all the missing information needed.</li><li>Click on “Save”.</li><li>Your revision has now been resubmitted for consideration by the {{appName}} Managing Board.</li></ol><p>Thanks again for your submission.</p><p>The Managing Board of {{appName}}</p>'
);
