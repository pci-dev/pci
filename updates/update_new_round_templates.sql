UPDATE mail_templates SET
subject = E'{{appName}}: Invitation to review a new version of a preprint you have already reviewed',
description = E'Mail to user already registered to indicate him/her that he/she is invited to re-review a preprint',
contents = E'
<p>Dear {{destPerson}},</p>
<p>I am handling the evaluation of the preprint entitled "{{art_title}}"), for potential recommendation by {{description}} ({{longname}}).</p>
<p>You have already evaluated this article as a reviewer in a previous round of review. This message is an invitation to review a new version of the preprint for a new round of evaluation.</p>
<p>A clean version of the revised manuscript can be viewed and downloaded at the following address: <a href="{{art_doi}}">{{art_doi}}</a></p>
<p>The authors have also supplied a tracked changes version of the manuscript and/or a response to reviewers. You will find these responses and files once you accept the review request and they can also be seen directly at the bottom of this message.</p>
<p>The evaluation process should guide the decision as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by {{longname}} is a complete article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.</p>
<p>If I eventually reach a favorable conclusion, all the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by {{longname}}, under the license CC-BY-ND. If after one or several rounds of review, I eventually reject the preprint, the editorial correspondence (and specifically your review) will NOT be published. You will be notified by e-mail at each stage of the procedure.</p>
<p>Please let me know as soon as possible whether you are willing to accept my invitation to review this revised version of this article, or whether you would prefer to decline, by clicking on the link below or by logging onto the {{longname}} website and going to ''For contributors —&gt; Invitation(s) to review a preprint'' in the top menu.</p>
<p>Thanks in advance for your help.</p>
<p>Yours sincerely,</p>
<p>{{sender}}</p>'
WHERE hashtag = '#DefaultReviewInvitationNewRoundRegisteredUser';

UPDATE mail_templates SET
subject = E'{{appName}}: Invitation to review a new version of a preprint you have already reviewed - reminder',
description = E'Mail to user already registered to remind him/her that he/she has been invited as a reviewer',
contents = E'
<p>Dear {{destPerson}},</p>
<p>This is a reminder concerning the following message, which you should already have received:</p>
<p>I am handling the evaluation of the preprint entitled "{{art_title}}"), for potential recommendation by {{description}} ({{longname}}).</p>
<p>You have already evaluated this article as a reviewer in a previous round of review. This message is an invitation to review a new version of the preprint for a new round of evaluation.</p>
<p>A clean version of the revised manuscript can be viewed and downloaded at the following address: <a href="{{art_doi}}">{{art_doi}}</a></p>
<p>The authors have also supplied a tracked changes version of the manuscript and/or a response to reviewers. You will find these responses and files once you accept the review request and they can also be seen directly at the bottom of this message.</p>
<p>The evaluation process should guide the decision as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by {{appLongName}} is a complete article that may be used and cited like any ‘classic’ article published in a peer-reviewed journal.</p>
<p>If you have already reviewed a previous version of this MS, please consider this message as an invitation to review a new version of the preprint for a new round of evaluation.</p>
<p>The evaluation process should guide the decision as to whether to ‘Revise’, ‘Recommend’ or ‘Reject’ the preprint. A preprint recommended by {{appLongname}} is a complete article that may be used and cited like any ‘classic’ article published in a peer-reviewed journals.</p>
<p>If I eventually reach a favorable conclusion, all the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by {{appLongname}}, under the license CC-BY-ND. If after one or several rounds of review, I eventually reject the preprint, the editorial correspondence (and specifically your review) will NOT be published. You will be notified by e-mail at each stage in the procedure.</p>
<p>Note that to avoid any conflict of interests you should not accept to evaluate this preprint if the authors are close colleagues (people belonging to the same laboratory/unit/department in the last four years, people with whom they have published in the last four years, with whom they have received joint funding in the last four years, or with whom they are currently writing a manuscript, or submitting a grant proposal), or family members, friends, or anyone for whom bias might affect the nature of your evaluation.</p>
<p>Please let me know as soon as possible whether you are willing to accept my invitation to review this revised version of this article, or whether you would prefer to decline, by clicking on the link below or by logging onto the {{appLongname}} website and going to ''For contributors —&gt; Invitation(s) to review a preprint'' in the top menu.</p>
<p>Thanks in advance for your help.</p>
<p>Yours sincerely,</p>
<p>{{recommenderName}}.</p>
<p>(Note that this message was automatically generated but I will also receive a copy of it)</p>
'
WHERE hashtag = '#ReminderReviewerInvitationNewRoundRegisteredUser';
