#!/bin/bash


date_load() {
	./all-pci-db.sh | while read db ; do
		psql -h mydb1 -p 33648 -U peercom $db -c "
		select last_alert from auth_user
		where alerts != 'Never'
		" | egrep "^ [0-9]"
	done
}

show_date_load() {
	date_load | sort | cut -c -14 | uniq -c
}

show_site_load() {
	./all-pci-db.sh | while read db; do
		printf "%25s" $db
		psql -h mydb1 -p 33648 -U peercom $db -c "
		select count(id) from auth_user
		where alerts = '$1'
		" | sed -n 3p
	done
}

main() {
	case $1 in
		""|-h|--help)
			echo "usage: $0 [date|site [freq]]"
			exit 0
			;;
		date)
			show_date_load
			;;
		site)
			case $2 in
				Weekly|Monthly|"Every two weeks"|"") ;;
				*) echo "invalid freq: $2"; exit 2 ;;
			esac
			show_site_load ${2:-Weekly}
			;;
		*)
			echo "unknown command: $1"
			exit 1
			;;
	esac
}

main "$@"
