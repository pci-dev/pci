UPDATE mail_templates
SET contents = REGEXP_REPLACE(contents, 'The +Managing +Board +of +PCI +\{\{appName\}\}', 'The Managing Board of {{appName}}', 'gi');

UPDATE mail_templates
SET contents = REGEXP_REPLACE(contents, 'The +Managing +Board +of +PCI', 'The Managing Board of {{appName}}', 'gi');
