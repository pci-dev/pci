#!/bin/bash

cd /data/www/peercommunityin/web2py/applications
python3 $1/updates/web2py.py -M -S pci -R applications/pci/updates/init_alert_date_and_current_step.py -A
cd -
