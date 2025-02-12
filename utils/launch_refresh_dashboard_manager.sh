#!/bin/bash

cd /data/www/peercommunityin/web2py || exit
find applications/ -type d -name "PCI*" | while read -r pci; do
    python3 web2py.py -M -S "$pci" -R "$pci"/updates/refresh_alert_date_and_current_step.py -A
done
cd - || exit
