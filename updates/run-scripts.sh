#!/bin/bash

cd $(dirname "$0")

usage() {
	echo "usage: $(basename "$0") <command>"
	show_options
}

run_scripts() {
	for script in *.py; do
		[ -f $script ] || {
			echo "no update scripts"
			break
		}

		grep -q "non-RR" <<< "$script" && \
		[ $DB = "pci_registered_reports" ] && \
		{
			echo "skipping non-RR update '$script'"
			continue
		}
		grep -q "RR-only" <<< "$script" && \
		[ $DB != "pci_registered_reports" ] && \
		{
			echo "skipping RR-only update '$script'"
			continue
		}
		echo "applying $script"
		./run $script || exit 3
	done
}

show_options() {
	echo
	echo "commands:"
	awk '/^\t-/' $0 | tr -d ')'
}

DB=$(grep psyco ../private/appconfig.ini | sed s:.*/::)

case $1 in
	""|-h|--help)
		usage
		;;
	-l|--list)
		ls *.py 2>/dev/null || echo "no *.py scripts"
		;;
	-a|--all)
		run_scripts
		;;
	-r|--reload)
		touch /var/www/peercommunityin/web2py/wsgihandler.py
		;;
	*)
		echo "unknown option: $1" && exit 1
		;;
esac
