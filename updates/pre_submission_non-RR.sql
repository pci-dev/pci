delete from mail_templates where hashtag = '#SubmitterGenericMail';
INSERT INTO "mail_templates"("hashtag","lang","subject","description","contents")
VALUES
(
E'#SubmitterGenericMail',
E'default',
E'{{appName}}: Revisions required to your submission',
E'Generic mail to submitters to fix errors in their submission',
E'<p>Dear {{destPerson}},</p><p>Thank you for the submission entitled <strong>{{articleTitle}}</strong>.<br><br>Before we can progress your submission, the following points need to be addressed:<br><br><br><strong>[MB member to insert points here]<br><br></strong></p><p>Please follow the steps below to revise your submission:</p><ol><li>Make the changes to the manuscript as instructed. We recommend using version control to keep the same URL to the submitted document, but if you decide to change the URL be sure to update any references to the URL in steps 3 and 4 below.</li><li>Once the revisions are made, login to the {{appName}} website and navigate to: <strong>For contributors</strong> &gt; <strong>Your submitted preprint.</strong></li><li>Find the submission that needs revising and click <strong>VIEW/EDIT.</strong></li><li>Click on “Edit preprint”. Update your submission and cover letter to respond to the points raised above and click “Save”.</li><li>Your revision has now been resubmitted for consideration by the {{appName}} Managing Board.</li></ol><p>Thanks again for your submission.</p><p>The Managing Board of {{appName}}</p>'
);
