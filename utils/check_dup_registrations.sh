#!/bin/bash


all_pci=$(grep psyco /var/www/peercommunityin/web2py/applications/PCI*/private/appconfig.ini | sed s:.*/::)

for db in $all_pci; do
    psql -h mydb1 -p 33648 -U peercom $db -c "select lower(email) from auth_user" > $db.users.lower.txt
    psql -h mydb1 -p 33648 -U peercom $db -c "select email from auth_user" > $db.users.txt
done

for f in *.lower.txt; do
    sort $f > $f.sorted
    sort -u $f > $f.unique
done

for f in *.lower.txt; do
    diff -u $f.sorted $f.unique
done | egrep '^-'
