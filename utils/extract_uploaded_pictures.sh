#!/bin/bash


PCI_DB=$1

PSQL="psql -h mydb1 -p 33648 -U peercom $PCI_DB"
#PSQL="psql -U postgres $PCI_DB"

main() {
	[ "$PCI_DB" ] || {
		echo "usage: $0 <pci_db>"
		exit 1
	}

	$PSQL -t -c "
	select id, uploaded_picture
	from t_articles
	where picture_data not null
	" | while read line; do
		id=`echo $line | cut -d "|" -f1`
		file=`echo $line | cut -d "|" -f2 | tr -d ' '`

		get_picture $id > uploads/$file
		printf "."
	done
	echo
}

get_picture() {
	$PSQL -t -c "
	select picture_data from t_articles where id=$1
	" | cut -c 4- | xxd -r -p | base64 -d
}

main "$@"
