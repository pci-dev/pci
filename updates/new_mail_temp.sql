INSERT INTO "mail_templates"("hashtag","lang","subject","description","contents")
VALUES
(
E'#RecommenderRejectMail',
E'default',
E'{{appName}}: Serious scientific or ethical issues pointed by a recommender',
E'Recommender mail to managers explaining why they rejected an invite',
E'<p>Dear members of the managing board,</p><p>I\'ve been invited to act as a recommender for the preprint entitled <strong>{{articleTitle}}</strong>, submitted by <strong>{{articleAuthors}}</strong>. I\'m declining this invitation because of the following serious scientific or ethical issues:</p><p><br><strong><em>**Please indicate here these serious scientific or ethical issues**<br><br></em></strong></p><p>Best regards,<br>{{recommenderPerson}}</p>'
);
