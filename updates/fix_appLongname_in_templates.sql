UPDATE mail_templates SET contents = replace(contents, '{{appLongname}}', '{{appLongName}}');
UPDATE mail_templates SET contents = replace(contents, '{{submitterName}}', '{{articleAuthors}}');
