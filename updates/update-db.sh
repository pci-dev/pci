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
EOF
}

update_rr() {
	update
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
