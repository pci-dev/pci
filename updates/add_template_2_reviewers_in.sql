INSERT INTO mail_templates (hashtag, lang, subject, description, contents)
VALUES
(
E'#ReminderRecommender2ReviewsReceivedCouldMakeDecision',
E'default',
E'{{appName}}: Editorial decision possible',
E'Mail to recommender to ask not to wait too long for additional reviews',
E'<p>Dear {{destPerson}},</p>
<p>
A few weeks ago, you should have received a notification that two reviews have been received for {{articleTitle}} by {{articleAuthors}}. We require a minimum of two reviews for each submission, so it is possible for you to make your editorial decision now. In the event that you are still waiting for additional reviews, we would like to ask you not to wait too long so as not to delay the article handling time. If you would like to make your decision without waiting for further reviews, please cancel the reviews that are not yet in, and then you will be able to make a decision.
</p>
<p>Thank you very much for handling this submission.</p>
<p>Best regards,</p>
<p>The Managing Board of {{appName}}</p>
'
);
