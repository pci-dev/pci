#!/bin/bash

PATH=$PATH:$(realpath $(dirname $0))

ALL_PCIs=$(all-pci-db.sh | grep -v compstat)

for pci in $ALL_PCIs; do
    for role in users reviewers recommenders authors; do
        get_users.sh $role $pci > $pci.$role.csv &
    done
done
wait

for role in users reviewers recommenders authors; do
	sed 1d *.$role.csv | awk -F ';' '{print $3}' | sort -u > all-$role-emails.csv
	sed 1d *.$role.csv | awk -F ';' '{print $3 ";" $1 ";" $2}' | sort -u > all-$role.csv
done
