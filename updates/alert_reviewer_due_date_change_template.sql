INSERT INTO mail_templates (hashtag, lang, subject, description, contents)
VALUES (
                '#RecommenderChangeReviewDueDate',
                'default',
                'Recommender change due date',
                'RecommenderChangeReviewDueDate',
                '<p>Dear {{destPerson}},</p>
<p>You have agreed to review the preprint entitled "<strong>{{articleTitle}}"</strong>&nbsp;(<a href="{{articleDoi}}">{{articleDoi}}</a>), submitted to {{appName}}, and we thank you for this contribution and for your support of PCI.</p>
<p>The deadline for the review has been changed by the recommender. <strong>Your review is now expected by {{dueDate}}</strong>.&nbsp;</p>
<p>To view, write, upload and manage your review, please follow this link <a href="{{myReviewsLink}}">{{myReviewsLink}}</a> or log onto the {{appName}} website and go to ‘For contributors —&gt; Your reviews’ in the top menu.</p>
<p>Guidelines for PCI reviewers can be found <a title="guideline for reviewers" href="https://peercommunityin.org/2020/10/22/pci-reviewer-guide/" target="_blank" rel="noopener">here</a>&nbsp;and a series of questions to help you conduct your review can be found <a href="https://peercommunityin.org/2022/05/20/questionnaire-for-reviewers/">here</a>.</p>
<p>Please note that for reasons of transparency, your review will be sent to the authors in its entirety, and no part of the review will be sent privately to the recommender, as is common practice in journals.</p>
<p>Thanks in advance for the time and energy spent evaluating this preprint! We look forward to reading your review.</p>
<p>Yours sincerely,</p>
<p>The managing board of {{appName}}</p>'
        );
