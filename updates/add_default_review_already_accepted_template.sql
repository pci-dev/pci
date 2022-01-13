INSERT INTO "mail_templates" ("hashtag","lang","subject","description","contents")
VALUES
(
E'#DefaultReviewAlreadyAcceptedCancellation',
E'default',
E'{{appName}}: About your review',
E'Mail to reviewer to indicate him/her a cancellation to review a preprint',
E'<p>Dear {{destPerson}},</p>\n<div>You kindly agreed to review the preprint entitled "{{art_title}}" by {{art_authors}} (DOI <a href="{{art_doi}}">{{art_doi}}</a>).</div>\n<div>&nbsp;</div>\n<div>Despite several reminders, we have not received your review yet. We hope that nothing serious has happened to you and that you are simply too busy. This message is to tell you that in order to move forward and give the authors an answer, we have decided to cancel your review. If you have any questions and if you have already written your review, please feel free to reply by return mail. Thank you in advance.</div>\n<p>I wish you all the best.</p>\n<p>Best regards,</p>\n<p>{{sender}}</p>'
);
