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

show_freq_load() {
	./all-pci-db.sh | while read db;
		do echo === $db ===
		psql -h mydb1 -p 33648 -U peercom $db -c "
		select alerts, last_alert from auth_user
		" | egrep '[0-9]$' | cut -c -30 | sort | uniq -c
	done
}

show_never() {
	./all-pci-db.sh | while read db; do
		echo === $db ===
		psql -h mydb1 -p 33648 -U peercom $db -c "
		select alerts, email, registration_datetime, last_alert
		from auth_user
		where alerts='Never'
		"
	done
}

main() {
	case $1 in
		""|-h|--help)
			echo "usage: $0 [date|site [freq]|all|never]"
			exit 0
			;;
		date)
			show_date_load
			;;
		site)
			case $2 in
				n) freq=Never;;
				w) freq=Weekly;;
				m) freq=Monthly;;
				b) freq="Every two weeks";;
				*)
				echo "invalid freq: $2";
				echo "use one of:"
				grep 'freq=' $0 | grep -v grep \
				| sed 's/;;//; s/ .*=/ /; s/^[[:space:]]*/\t/'
					exit 2 ;;
			esac
			show_site_load $freq
			;;
		all)
			show_freq_load
			;;
		never)
			show_never
			;;
		*)
			echo "unknown command: $1"
			exit 1
			;;
	esac
}

main "$@"
