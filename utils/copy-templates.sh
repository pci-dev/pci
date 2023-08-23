#/bin/bash

DB=$1
TARGET=${2:-_}

parse_args() {
	declare -A target=(
		[test]="pci-test psql --csv -U postgres"
		[prod]="pci-prod psql --csv -U peercom -h mydb1 -p 33648"
	)
	TARGET=${target[$TARGET]}

	[ "$DB" ] && [ "$TARGET" ] || {
		echo "usage: $0 <pci_db> <test|prod>"
		exit 1
	}
}

copy_templates() {
	ssh $TARGET $DB << EOT
	select hashtag, contents
	from mail_templates
	where hashtag in (
		'#DefaultReviewInvitationNewUser',
		'#DefaultReviewInvitationRegisteredUser',
		'#ReminderReviewerReviewInvitationNewUser',
		'#ReminderReviewerReviewInvitationRegisteredUser'
	)
	order by hashtag;
EOT
}

parse_args
copy_templates

# pci_evolbiol_test
# pci_registered_reports_new

# then, manually patch csv to make it an 'update' .sql:
# 1.) sed "s/'/''/g"
# 2.) sed 's/""/"/g'
# 3.) remove <hashtag>, column
# 4.) add the following head sql as first line above block:
#           update mail_templates set contents = '
# 5.) add the following final sql as last line below block:
#           where hashtag = '<hashtag>';
