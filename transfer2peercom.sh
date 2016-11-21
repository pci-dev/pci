#!/bin/bash

rsync --verbose --stats --progress --recursive --perms --usermap=peercom:www-data --times --copy-links --update --delete --delete-before --exclude='*~' --exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' --exclude 'errors' --exclude '*.ini' --exclude '*.old' -e "ssh -i /home/piry/.ssh/id_rsa_pci" ~/W/web2py/applications/pcidev/ peercom@peercom-front1:/var/www/peercommunityin/web2py/applications/PCIEvolBiol

# echo 'TRUNCATE help_texts;' | psql -h mbipi pci_evolbiol
# pg_dump -h gaia2 -p 5432 -F p -N work -t help_texts -b --data-only --inserts --column-inserts -O -d pci_evolbiol | psql -h mbipi pci_evolbiol

# /opt/rubyrep-1.2.0/rubyrep sync -c ~/W/Labo/PCiEvolBiol/rr_help.conf

