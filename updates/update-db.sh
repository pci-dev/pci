#!/bin/bash

DB=$1

usage() {
	echo "usage: $(basename "$0") <database>"
}

# all_pci=$(grep psyco /var/www/peercommunityin/web2py/applications/PCI*/private/appconfig.ini | sed s:.*/::)

if id | grep -q peercom; then
PSQL="psql -h mydb1 -p 33648 -U peercom"
else
PSQL="psql -U postgres"
fi

update() {
$PSQL $DB << EOF
-- 30/09/2021

\set TEMPLATE_TEXT '<p>Dear {{destPerson}},</p>\n<p>Regarding your review of the preprint entitled <strong>{{articleTitle}}</strong>,<br><br><br><b><em>**You can edit/write your message to the referee**</em></b><br><br><br></p>\n<p>We thank you again for evaluating this preprint.</p>\n<p>All the best,<br>{{recommenderPerson}} at {{appName}}</p>'
\set DESCRIPTION 'Generic mail to reviewers for recommender/managers to notify any additional information'
\set SUBJECT '{{appName}}: about your peer review'

INSERT INTO "public"."mail_templates"("hashtag","lang","subject","description","contents")
VALUES
(E'#ReviewerGenericMail',E'default',:'SUBJECT',:'DESCRIPTION',:'TEMPLATE_TEXT');
EOF
}

update_rr() {
$PSQL $DB << EOF
EOF
}

case $DB in
	""|-h|--help)
		usage
		;;
	pci_registered_reports)
		update_rr
		;;
	*)
		update
		;;
esac
