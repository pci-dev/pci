#!/bin/bash

BASE=/var/www/peercommunityin/web2py/applications
RUN=cron_tasks/run

while true; do
    $BASE/PCIEcology/$RUN import_biorxiv_xml.py
    sleep ${2:-1m}
done
