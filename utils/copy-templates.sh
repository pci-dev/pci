#/bin/bash

copy_eb3_templates() {
ssh pci-test \
psql -U postgres pci_evolbiol_test --csv << EOT
	select hashtag, contents
	from mail_templates
	where hashtag in (
		'#ReminderReviewerReviewSoonDue',
		'#ReminderReviewerReviewDue',
		'#ReminderReviewerReviewOverDue'
	);
EOT
}

copy_rr3_templates() {
ssh pci-test \
psql -U postgres pci_registered_reports_new --csv << EOT
	select hashtag, contents
	from mail_templates
	where hashtag in (
'#ReminderReviewerReviewSoonDueStage1',
'#ReminderReviewerReviewSoonDueStage2',
'#ReminderReviewerReviewDueStage1',
'#ReminderReviewerReviewDueStage2',
'#ReminderReviewerReviewOverDueStage1',
'#ReminderReviewerReviewOverDueStage2'
	);
EOT
}

#copy_rr3_templates
copy_eb3_templates

# then, manually patched csv to make it an 'update' .sql:
# 1.) sed "s/'/''/g"
# 2.) sed 's/""/"/d'
# 3.) remove <hashtag>, column
# 4.) add the following head sql as first line above block:
#           update mail_templates set contents = '
# 5.) add the following final sql as last line below block:
#           where hashtag = '<hashtag>';
