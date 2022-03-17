#!/bin/bash

ALL_PCIs=$(../all-pci-db.sh | grep -v compstat)

for pci in $ALL_PCIs; do
    for role in users reviewers recommenders authors; do
        ../get_users.sh $role $pci > $pci.$role.csv &
    done
done
wait
