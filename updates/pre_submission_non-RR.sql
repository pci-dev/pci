delete from mail_templates where hashtag = '#SubmitterGenericMail';
INSERT INTO "mail_templates"("hashtag","lang","subject","description","contents")
VALUES
(
E'#SubmitterGenericMail',
E'default',
E'{{appName}}: Update on your submission',
E'Generic mail to submitters to fix errors in their submission',
E'<p>Dear {{destPerson}},</p>\n<p>Regarding the submission of your report entitled <strong>{{articleTitle}}</strong>,<br><br><br><b><em>**You can edit/write your message to the referee**</em></b><br><br><br></p><p>Thanks again for this submission.</p>\n<p>The managing board of {{appName}}</p>'
);
