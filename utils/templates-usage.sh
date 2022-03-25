#!/bin/bash


for db in pci_ecology pci_evolbiol; do
	for who in senders recipients all; do
		psql -t -A -F'	' -h mydb1 -p 33648 -U peercom $db \
		< templates-usage.$who.sql > $db.templates-usage.$who.csv
	done
done
