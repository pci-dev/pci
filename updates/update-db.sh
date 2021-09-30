#!/bin/bash

DB=$1

usage() {
	echo "usage: $(basename "$0") <database>"
}

# all_pci=$(grep psyco /var/www/peercommunityin/web2py/applications/PCI*/private/appconfig.ini | sed s:.*/::)

PSQL="psql -h mydb1 -p 33648 -U peercom"

update() {
$PSQL $DB << EOF
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
