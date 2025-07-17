#!/bin/bash

B2J_SITES=$(<$0.list)

BASE=/var/www/peercommunityin/web2py/applications
RUN=cron_tasks/run

while true; do
    for pci in $B2J_SITES; do
	$BASE/$pci/$RUN import_biorxiv_xml.py
    done
    sleep ${2:-1m}
done
