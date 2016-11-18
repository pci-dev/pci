#!/bin/bash

unison -auto -ignore "Name appconfig.ini" -ignore "Name crontab" -ignore "Name *~" -ignore "Name *.bak" -ignore "Name *.pyc" -ignore "Name .git" -ignore "Name sessions" -ignore "Name errors" -sshargs -C  ~/W/web2py/applications/pcidev   ssh://www-data@gaia2//home/www-data/web2py/applications/PCiEvolBiol

unison -auto -ignore "Name appconfig.ini" -ignore "Name crontab" -ignore "Name *~" -ignore "Name *.bak" -ignore "Name *.pyc" -ignore "Name .git" -ignore "Name sessions" -ignore "Name errors" -sshargs -C  ~/W/web2py/applications/pcidev   ssh://priono//home/piry/web2py/applications/PCIEvolBiol


echo 'TRUNCATE help_texts;' | psql -h mbipi pci_evolbiol
pg_dump -h gaia2 -p 5432 -F p -N work -t help_texts -b --data-only --inserts --column-inserts -O -d pci_evolbiol | psql -h mbipi pci_evolbiol

# /opt/rubyrep-1.2.0/rubyrep sync -c ~/W/Labo/PCiEvolBiol/rr_help.conf

