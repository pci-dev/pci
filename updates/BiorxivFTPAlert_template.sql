delete from mail_templates where hashtag = '#BiorxivFTPAlert';

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#BiorxivFTPAlert','default','Biorvix FTP Alert','Biorvix FTP Alert','<p>Pre-submission from bioRxiv received on our FTP.</p>
<p>Content:</p>
<p>{{xmlContent}}</p>
<p>&nbsp;</p>');
