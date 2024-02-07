update mail_templates
set contents = replace(contents, 'PCI {{appName}}', '{{appName}}');
