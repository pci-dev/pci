#!/bin/bash

DIR=$(dirname $(realpath "$0"))
list=$($DIR/all-pci-test-sites.sh)
conf=$DIR/.test-sites.conf

usage() {
	echo "$0 <eb|rr|PCi<SITE>|all|check> [-f]"
}

main() {
	case $2 in
		-f|--force)
			force=force
			;;
	esac
	case $1 in
		""|-h|--help)
			usage
			exit 0
			;;
		eb)
			update PCiEvolBiol3 $force
			;;
		rr)
			update PCiRR3 $force
			;;
		PCi*)
			update $1 $force
			;;
		all)
			update_all
			;;
		check)
			check="version"
			update_all
			;;
	esac
}

update() {
	site=$1
	update=${2:-update}
	curl -s -u "$auth" $base/$site/dev/$update
}

update_all() {
	tmp=$(mktemp)

	for site in $list; do
	(
		result=$(update $site "$check" | tail -2 | head -1)
		printf "%-20s: %s\n" "$site" "$result"
	) >> $tmp &
	done
	wait
	sort $tmp
	rm $tmp
}

init() {
	source $conf || {
		[ -f $conf ] || {
			cp $conf.sample $conf
			echo "$conf created.  Please edit and set password."
			exit 1
		}
		echo "$conf: error in conf"
		exit 2
	}
	for var in base auth; do
		[ "${!var}" ] || {
			echo "$conf: $var not set"
			exit 3
		}
	done
}

init
main "$@"
