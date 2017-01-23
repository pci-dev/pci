#!/bin/bash

# GAIA2
unison -auto -ignore "Name *.ini" -ignore "Name crontab" -ignore "Name *~" -ignore "Name *.bak" -ignore "Name *.pyc" -ignore "Name .git" -ignore "Name sessions" -ignore "Name errors" -sshargs -C  ~/W/web2py/applications/pcidev   ssh://www-data@gaia2//home/www-data/web2py/applications/PCiEvolBiol

# PRIONO
# ~/bin/unison-2.48.3 -auto -ignore "Name *.ini" -ignore "Name crontab" -ignore "Name *~" -ignore "Name *.bak" -ignore "Name *.pyc" -ignore "Name .git" -ignore "Name sessions" -ignore "Name errors" -sshargs -C  ~/W/web2py/applications/pcidev   ssh://priono//home/piry/web2py/applications/PCIEvolBiol
rsync --verbose --stats --progress --recursive --perms --usermap=peercom:www-data --times --copy-links --update --delete --delete-before --exclude='*~' --exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' --exclude 'errors' --exclude '*.ini' --exclude '*.old' ~/W/web2py/applications/pcidev/ priono:/home/piry/web2py/applications/PCIEvolBiol


exit

# HELP TEXTS
# echo 'TRUNCATE help_texts;' | psql -h mbipi pci_evolbiol
# pg_dump -h gaia2 -p 5432 -F p -N work -t help_texts -b --data-only --inserts --column-inserts -O -d pci_evolbiol | psql -h mbipi pci_evolbiol

# /opt/rubyrep-1.2.0/rubyrep sync -c ~/W/Labo/PCiEvolBiol/rr_help.conf

