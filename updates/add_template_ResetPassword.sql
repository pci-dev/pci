delete from mail_templates where hashtag = '#UserResetPassword';
insert into mail_templates
(hashtag, description, lang, subject, contents) values (
'#UserResetPassword',
'Mail to user to reset their password',
'default',
'{{appName}}: Reset password',
'<p>You requested to reset your password. Please click the following link: <a href="{{linkTarget}}">reset password</a>.</p><br><p>Thank you for your time and support.</p>'
);
