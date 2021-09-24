#!/bin/bash

PCI=$1

[ -d "$PCI" ] || { echo "usage: $(basename "$0") <PCI directory>"; exit 1; }

# all_pci=$(grep psyco /var/www/peercommunityin/web2py/applications/PCI*/private/appconfig.ini | sed s:.*/::)


update() {
	git fetch
	git merge
}

update
