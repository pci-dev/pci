delete from mail_templates where hashtag = '#BiorxivFTPAlert';

INSERT INTO mail_templates (hashtag,lang,subject,description,contents) VALUES
	 ('#BiorxivFTPAlert','default','Biorvix FTP Alert','Biorvix FTP Alert','<p>A new Biorxiv FTP file has arrived on the server.</p>
<p>Content:</p>
<p>{{xmlContent}}</p>
<p>&nbsp;</p>');
