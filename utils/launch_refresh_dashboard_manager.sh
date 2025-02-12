#!/bin/bash

cd /data/www/peercommunityin/web2py || exit
find applications/ -type d -name "PCI*" | while read -r pci; do
    python3 web2py.py -M -S "$pci" -R "$pci"/utils/refresh_dashboard_manager.py -A
done
cd - || exit
