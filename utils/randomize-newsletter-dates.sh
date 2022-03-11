#!/bin/bash

set_psql() {
	if id | grep -q peercom; then
		PSQL="psql -h mydb1 -p 33648 -U peercom"
	else
		PSQL="psql -U postgres"
	fi
	PSQL="$PSQL -v ON_ERROR_STOP=1"
}

randomize_newsletter_base_dates() {
	$PSQL $DB -c "
	update auth_user
	set last_alert = timestamp '2022-02-28'
        		+ random() * INTERVAL '5 days'
	where alerts != 'Never';
	"
}

main() {
	case $1 in
	""|-h|--help)
		echo "usage: $0 <pci_db>"
		exit 0
	;;
	esac

	set_psql
	set -x
	DB=$1
	randomize_newsletter_base_dates
}

main "$@"
