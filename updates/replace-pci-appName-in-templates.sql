update mail_templates
set contents = replace(contents, 'PCI {{appName}}', '{{appName}}')

where contents ~ 'PCI {{appName}}';
