#!/bin/bash

# SYNC SOURCE CODE FROM MBIPI TO WEBSITE
rsync --verbose --stats --progress --recursive --perms --usermap=peercom:www-data --times --copy-links --update --delete --delete-before --exclude='*~' --exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' --exclude 'errors' --exclude '*.ini' --exclude '*.old' ~/W/web2py/applications/pcidev/ peercom@peercom-front1:/var/www/peercommunityin/web2py/applications/PCIEvolBiol

# SYNC SOURCE CODE FROM PRIONO TO WEBSITE
# rsync --verbose --stats --progress --recursive --perms --usermap=peercom:www-data --times --copy-links --update --delete --delete-before --exclude='*~' --exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' --exclude 'errors' --exclude '*.ini' --exclude '*.old' /home/piry/web2py/applications/PCIEvolBiol/ peercom@peercom-front1:/var/www/peercommunityin/web2py/applications/PCIEvolBiol

exit

# HELP FROM GAIA2 TO WEBSITE
# echo 'TRUNCATE help_texts;' | ssh peercom@peercom-front1 'psql -h mydb1 -U peercom pci_evolbiol'
# pg_dump -h gaia2 -p 5432 -F p -N work -t help_texts -b --data-only --inserts --column-inserts -O -d pci_evolbiol | ssh peercom@peercom-front1 'psql -h mydb1 -U peercom pci_evolbiol'
# exit


# # HELP FROM GAIA2 TO MBIPI
# echo 'TRUNCATE help_texts;' | psql -h mbipi pci_evolbiol
# pg_dump -h gaia2 -p 5432 -F p -N work -t help_texts -b --data-only --inserts --column-inserts -O -d pci_evolbiol | psql -h mbipi pci_evolbiol
# exit
# 
# SYNCHRO TRY .... DON'T EXECUTE
# /opt/rubyrep-1.2.0/rubyrep sync -c ~/W/Labo/PCiEvolBiol/rr_help.conf


# # HELP FROM WEBSITE TO MBIPI
# echo 'TRUNCATE help_texts;' | psql -h mbipi pci_evolbiol
# ssh peercom@peercom-front1 'pg_dump -h mydb1 -p 5432 -U peercom -Fp -t help_texts -b --data-only --inserts --column-inserts -O -d pci_evolbiol' | psql -h mbipi pci_evolbiol
# exit
