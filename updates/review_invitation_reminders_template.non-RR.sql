delete from mail_templates where hashtag in (
	'#ReminderReviewerReviewDue',
    '#ReminderReviewerReviewSoonDue',
    '#ReminderReviewerReviewOverDue'
);

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#ReminderReviewerReviewDue','default','{{appName}}: Review due - reminder','Mail to reviewer to indicate a review due','<p>Dear {{destPerson}},</p>
<p>This is a reminder for your review of the preprint "<strong>{{articleTitle}}</strong>" that is due today.</p>
<p>To view, write, upload and manage your review, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or log onto the {{appName}} website and go to ‘For contributors —&gt; Your reviews’ in the top menu.</p>
<p>Guidelines for PCI reviewers can be found <a title="guideline for reviewers" href="https://peercommunityin.org/2020/10/22/pci-reviewer-guide/" target="_blank" rel="noopener">here</a>&nbsp;and a series of questions to help you conduct your review can be found <a href="https://peercommunityin.org/2022/05/20/questionnaire-for-reviewers/">here</a>.</p>
<p>Please note that for reasons of transparency, your review will be sent to the authors in its entirety, and no part of the review will be sent privately to the recommender, as is common practice in journals.</p>
<p>In case of any problem or difficulties, or if you need an extension, please contact <a href="{{appContactMail}}">{{appContactMail}}</a>.</p>
<p>Many thanks in advance for completing your review.</p>
<p>Best regards</p>
<p>The managing board of {{appName}}</p>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#ReminderReviewerReviewSoonDue','default','{{appName}}:  Review soon due','Mail to reviewer to indicate a review soon due','<p>Dear {{destPerson}},</p>
<p>You have agreed to review the preprint entitled "<strong>{{articleTitle}}"</strong>&nbsp;(<a href="{{articleDoi}}">{{articleDoi}}</a>), submitted to {{appName}}, and we thank you for this contribution and for your support of PCI.</p>
<p>The deadline for the review is coming up on {{reviewDueDate}}. If you need more time, please let us know by email.</p>
<p>To view, write, upload and manage your review, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or log onto the {{appName}} website and go to ‘For contributors —&gt; Your reviews’ in the top menu.</p>
<p>Guidelines for PCI reviewers can be found <a title="guideline for reviewers" href="https://peercommunityin.org/2020/10/22/pci-reviewer-guide/" target="_blank" rel="noopener">here</a>&nbsp;and a series of questions to help you conduct your review can be found <a href="https://peercommunityin.org/2022/05/20/questionnaire-for-reviewers/">here</a>.</p>
<p>Please note that for reasons of transparency, your review will be sent to the authors in its entirety, and no part of the review will be sent privately to the recommender, as is common practice in journals.</p>
<p>Thanks in advance for the time and energy spent evaluating this preprint! We look forward to reading your review.</p>
<p>Yours sincerely,</p>
<p>The managing board of {{appName}}</p>');

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#ReminderReviewerReviewOverDue','default','{{appName}}: Review overdue','Mail to reviewer to indicate a review overdue','<p>Dear {{destPerson}},</p>
<p>This is a reminder that your review of the preprint <strong>{{articleTitle}}</strong>&nbsp;was due a few days ago.</p>
<p>We fully understand the huge number of deadlines you might face, but we also know how frustrating it can be, as an author, to wait upon reviews.&nbsp;</p>
<p>To keep the PCI process friendly, could you please let us know (<a href="{{appContactMail}}">{{appContactMail}}</a>) when we can expect your review?</p>
<p>To view, write, upload and manage your review, please follow this link <a href="{{linkTarget}}">{{linkTarget}}</a> or log onto the {{appName}} website and go to ‘For contributors —&gt; Your reviews’ in the top menu.</p>
<p>Guidelines for PCI reviewers can be found <a title="guideline for reviewers" href="https://peercommunityin.org/2020/10/22/pci-reviewer-guide/" target="_blank" rel="noopener">here</a>&nbsp;and a series of questions to help you conduct your review can be found <a href="https://peercommunityin.org/2022/05/20/questionnaire-for-reviewers/">here</a>.</p>
<p>Many thanks in advance for completing your review.</p>
<p>Best regards</p>
<p>The managing board of {{appName}}</p>');
