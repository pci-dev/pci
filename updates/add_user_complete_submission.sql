delete from mail_templates where hashtag in (
	'#UserResetPassword',
	'#UserCompleteSubmissionCOAR',
	'#UserCompleteResubmissionCOAR'
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
INSERT INTO mail_templates (hashtag, lang, subject, description, contents)
VALUES
(
E'#UserCompleteResubmissionCOAR',
E'default',
E'{{appName}}: Please complete your resubmission made from a preprint server',
E'Mail to submitter when resubmission made from a preprint server via COAR',
E'<p>Dear {{destPerson}}</p><p>Thank you for your resubmission made via a preprint server and sent to {{appName}}.</p><p>Please click on the following link: <a href="{{linkTarget}}" data-mce-href="{{linkTarget}}">Complete your resubmission</a><br data-mce-bogus="1"></p><p>and complete your submission as follows:</p><p>1) Check the title, authors, DOI, abstract, keywords, disciplines, and DOI/URL of data, scripts and code. Do not forget to save your modifications by clicking on the green button.</p><p>2) Click on the blue ‘EDIT YOUR REPLY TO THE RECOMMENDER’ button (mandatory step). You could then write or paste your text, upload your reply as a PDF file, and upload a document with the modifications marked in TrackChange mode. If you are submitting the final formatted version ready to be recommended, you should only add a sentence indicating that you posted the final version on the preprint server. Do not forget to <strong>save your modifications by clicking on the green button</strong>.</p><p>3) Click on the green ‘SEND RESUBMISSION’ button. This will result in your submission being sent to the recommender.</p><p>Once the recommender has read the revised version, they may decide to recommend it directly, in which case the editorial correspondence (reviews, recommender’s decisions, authors’ replies) and a recommendation text will be published by {{appName}} under the license CC-BY.</p><p>Alternatively, other rounds of reviews may be needed before the recommender reaches a favorable conclusion. They may also reject your article, in which case the reviews and decision will be sent to you, but they will not be published or publicly released by {{appName}}. They will be safely stored in our database, to which only the Managing Board has access. You will be notified by e-mail at each stage in the procedure.</p><p>We thank you in advance for submitting your revised version.</p><p>Yours sincerely,</p><p>The Managing Board of {{appName}}</p>'
);
