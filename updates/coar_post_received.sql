delete from mail_templates where hashtag = '#AdminReportCOARPostReceived';
INSERT INTO public.mail_templates (hashtag,lang,subject,description,contents) VALUES
('#AdminReportCOARPostReceived','default',
'{{appName}}: COAR submission received',
'Mail to notify admins that coar_notify/inbox received a POST request',
'
<p>Dear PCI Team,</p>
<p>{{appName}} just received a COAR Notify endorsement request from {{author_email_link}} for {{submission_doi_link}}.</p>
<p>Details about this submission can be found <a href="{{notification_link}}">here</a>.</p>
<p>
 Except for duplicate or invalid submissions, a pre-submission should now be place in {{appName}} and an email
 has been sent to the authors requesting that they complete their submission in the {{appName}} website.
 The email was cc/bcc-ed to managers and to the contact mailbox of {{appName}}.
</p>
<p>Please ensure that this pre-submission is in place in {{appName}}. If not, contact the PCI developers as soon as possible.</p>
<p>Thanks!</p>
<p><br>The COAR Notify sub-system at {{appName}}</p>
');
