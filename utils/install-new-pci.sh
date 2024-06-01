#!/bin/bash

pci_db=pci_healthmovsci
logo_base=logo-PCIhealthmovsci.png


main() {
	[ "$1" ] || usage

	$1
}

usage() {
	echo "usage: $0 <action>"
	echo
	echo "actions:"
	egrep '^[a-z]+_[a-z]+\(\)' $0 | sed 's/^/\t/; s/().*//'
	echo
	echo "current config:"
	echo "	db: $pci_db"
	echo "	logos: $logo_base"

	chkconfig
}

init_db() {
	PSQL < sql_dumps/pci_evolbiol_test.sql
	PSQL < sql_dumps/t_status_article.sql
	PSQL < sql_dumps/pci_evolbiol_test_data0.sql
	utils/import-from-eb.sh
}

init_logos() {
	mv small-$logo_base static/images/small-background.png
	mv $logo static/images/background.png
}

update_crontab() {
	app_dir=$(basename $PWD)
	(
	crontab -l
	printf "\nSITE=$app_dir\n"
	crontab -l | tac | sed '/SITE=/,$ d' | tac
	) | crontab

	crontab -l | tail
}

update_gitauth() {
	echo "    directory = `realpath $PWD`" >> /var/www/.gitconfig
}

chkconfig() {
       	ls {small-,}$logo_base > /dev/null
	PSQL <<< '\d'
}

PSQL() {
	(db=$PCI_DB; psql -t -h mydb1 -p 33648 -U peercom $db)
}


main "$@"
