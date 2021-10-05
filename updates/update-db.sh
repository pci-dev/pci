#!/bin/bash

DB=$1

usage() {
	echo "usage: $(basename "$0") <database>"
	show_options
}

set_psql() {
	if id | grep -q peercom; then
		PSQL="psql -h mydb1 -p 33648 -U peercom"
	else
		PSQL="psql -U postgres"
	fi
}

get_local_db() {
	cat private/appconfig.ini | db_from_config
}

db_from_config() {
	grep psyco | sed s:.*/::
}

get_all_db() {
	ROOT=/var/www/peercommunityin/web2py/applications
	cat $ROOT/PCI*/private/appconfig.ini | db_from_config
}

apply_db() {
	$PSQL $DB < $(dirname "$0")/$1
}

show_options() {
	echo
	echo "options:"
	awk '/^\t-/' $0 | tr -d ')'
}

set_psql

case $1 in
	""|-h|--help)
		usage
		;;
	-l|--list)
		get_all_db
		;;
	-d|--local-dir)
		$0 $(get_local_db)
		;;
	-a|--all)
		for db in $(get_all_db); do $0 $db; done
		;;
	 -*)
		echo "unknown option: $1" && exit 1
		;;
	pci_registered_reports)
		apply_db update_rr.sql
		;;
	*)
		apply_db update.sql
		;;
esac
