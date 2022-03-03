UPDATE mail_templates SET contents = replace(contents, '{{reviewLimitText}}', '{{reviewDuration}}');
UPDATE mail_templates SET contents = replace(contents, 'three weeks', '{{reviewDuration}}');
UPDATE mail_templates SET contents = replace(contents, '14 days', '{{reviewDuration}}');
