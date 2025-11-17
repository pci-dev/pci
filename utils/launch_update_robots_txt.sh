#!/bin/bash

cd /data/www/peercommunityin/web2py || exit
find applications/ -maxdepth 1 -type d \( -name "PCI*" -o -name "TEST" -o -name "EB3" -o -name "RR3" \) | while read -r pci; do
    app="${pci##*/}"
    echo "=== $app ==="
    python3 web2py.py -M -S "$app" -R "$pci"/utils/update_robots_txt.py -A
done
cd - || exit
