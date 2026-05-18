DELETE
FROM mail_templates
WHERE hashtag = '#DefaultReviewAlreadyAcceptedCancellation'
;

INSERT INTO mail_templates
(hashtag, lang, subject, description, contents)
VALUES (
    '#DefaultReviewAlreadyAcceptedCancellation',
    'default',
    '{{appName}}: About your review',
    'Mail to reviewer to indicate them a cancellation to review a preprint',
    '<p>Dear {{destPerson}},</p>
<div>You kindly agreed to review the preprint entitled "<strong>{{art_title}}</strong>" by {{art_authors}} (<a href="{{art_doi}}">{{art_doi}}</a>).</div>
<div>&nbsp;</div>
<div>
<div>I am writing to let you know that we have decided to move ahead with an editorial decision on this manuscript without your evaluation.</div>
<div>&nbsp;</div>
<div>If you have any questions and if you have already written your review, please feel free to reply by return email and we will include it in the evaluation. Thank you in advance.</div>
<div>&nbsp;</div>
<p>Best regards,</p>
</div>
<p>{{sender}}</p>'
);
