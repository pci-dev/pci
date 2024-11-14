#!/bin/bash

cd /data/www/peercommunityin/web2py
python3 web2py.py -M -S $1 -R applications/$1/updates/refresh_alert_date_and_current_step.py -A
cd -
