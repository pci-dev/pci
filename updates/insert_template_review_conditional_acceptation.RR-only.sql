delete from mail_templates where hashtag in (
	'#ReminderRecommenderAcceptationReview',
    '#RecommenderDeclineReviewNewDelay',
    '#RecommenderAcceptReviewNewDelay',
    '#ConditionalRecommenderAcceptationReview'
);

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#ReminderRecommenderAcceptationReview','default','{{appName}}: A reviewer agrees to review, but asks for more time - reminder','reminder delayReminder to the recommender to tell them that a reviewer agreed to review pending an extra duration time','<p><strong>A friendly reminder</strong><span style="font-weight: 400;">.<br></span><span style="font-weight: 400;">{{message}}</span></p>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#RecommenderDeclineReviewNewDelay','default','{{appName}}: Your request for extra review duration has been declined','Email indicating the reviewer that the recommender has declined their request to have an extra delay to make their review','<p>Dear {{destPerson}},</p>
<p>Your request for an extra review duration time to review the report entitled "<strong>{{articleTitle}}</strong>" has been declined by the recommender.</p>
<p>Hence, please do not start reviewing this report.</p>
<p>Thanks again for your willingness to review, and we are sorry that it does not align with the recommender''s timing.</p>
<p>We hope you''ll remain motivated to review other report for {{appName}}.</p>
<p>Yours sincerely,</p>
<p>The managing board of {{appName}}</p>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#RecommenderAcceptReviewNewDelay','default','{{appName}}: Your request for extra review duration has been accepted','Mail to a reviewer to tell them that the recommender has accepted their request for an extra review duration time','<p>Dear {{destPerson}},</p>
<p>Your request for an extra review duration time to review the report entitled "<strong>{{articleTitle}}</strong>" (<a href="{{articleDoi}}">{{articleDoi}}</a>) has been accepted by the recommender. <br><br>Hence, please complete your review within {{reviewDuration}} (i.e. by <strong>{{dueTime}}</strong>).&nbsp;</p>
<p>To view, write, upload and manage your review, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or log onto the {{appName}} website and go to ‘For contributors —&gt; Your reviews’ in the top menu.</p>
<p>Please note that for reasons of transparency, your review will be sent to the authors in its entirety, and no part of the review will be sent privately to the recommender, as is common practice in journals.</p>
<p>Thanks in advance for the time spent evaluating this report! We look forward to reading your review.</p>
<p>Yours sincerely,</p>
<p>The managing board of {{appName}}</p>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#ConditionalRecommenderAcceptationReview','default','{{appName}}: A reviewer agrees to review, but asks for more time','Mail to the recommender to tell them that a reviewer agreed to review pending an extra duration time','<p>Dear {{destPerson}},</p>
<p>You have initiated the evaluation of the article entitled&nbsp;<strong>{{articleTitle}}</strong> by {{articleAuthors}} (<a href="{{articleDoi}}">{{articleDoi}}</a>).</p>
<p>You invited {{reviewerPerson}} to review this report. They accepted your invitation but only if the delay to review the article <strong>can be extended to {{delay}}</strong>.</p>
<p>You can accept or decline this offer by clicking on the corresponding button below<br><br>Thanks again for managing this evaluation.</p>
<p>Yours sincerely,</p>
<p>The Managing Board of {{appName}}</p>');
