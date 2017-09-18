#!/bin/bash -x

# GAIA2
~/bin/unison-2.40.61 -auto \
	-ignore "Name *.ini" \
	-ignore "Name crontab" \
	-ignore "Name *~" \
	-ignore "Name *.bak" \
	-ignore "Name *.pyc" \
	-ignore "Name *.orig" \
	-ignore "Name .git" \
	-ignore "Name sessions" \
	-ignore "Name errors" \
	-ignore "Name *background.png" \
	-sshargs -C  \
	~/W/web2py/applications/pcidev   ssh://www-data@gaia2//home/www-data/web2py/applications/PCiEvolBiol

ssh www-data@gaia2 "find /home/www-data/web2py/applications/PCiEvolBiol -name \\*.pyc -ls ; find /home/www-data/web2py/applications/PCiEvolBiol -name \\*.pyc -exec rm {} \\; ; touch /home/www-data/web2py/wsgihandler.py"

# echo "UPDATE t_reviews SET review_state='Completed' WHERE review_state LIKE 'Terminated';" | psql -h gaia2 -U piry pci_evolbiol
# echo "SELECT DISTINCT review_state FROM t_reviews;" | psql -h gaia2 -U piry pci_evolbiol
# echo "ALTER TABLE public.t_recommendations ADD COLUMN track_change character varying(512); ALTER TABLE public.t_recommendations ADD COLUMN track_change_data bytea;" | psql -h gaia2 -U piry pci_evolbiol


# PRIONO
# ~/bin/unison-2.48.3 -auto -ignore "Name *.ini" -ignore "Name crontab" -ignore "Name *~" -ignore "Name *.bak" -ignore "Name *.pyc" -ignore "Name .git" -ignore "Name sessions" -ignore "Name errors" -sshargs -C  ~/W/web2py/applications/pcidev   ssh://priono//home/piry/web2py/applications/PCIEvolBiol
# rsync --verbose --stats --progress --recursive --perms --usermap=peercom:www-data --times --copy-links --update --delete --delete-before --exclude='*~' --exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' --exclude 'errors' --exclude '*.ini' --exclude '*.old' ~/W/web2py/applications/pcidev/ priono:/home/piry/web2py/applications/PCIEvolBiol


exit

# HELP TEXTS
# echo 'TRUNCATE help_texts;' | psql -h mbipi pci_evolbiol
# pg_dump -h gaia2 -p 5432 -F p -N work -t help_texts -b --data-only --inserts --column-inserts -O -d pci_evolbiol | psql -h mbipi pci_evolbiol

# /opt/rubyrep-1.2.0/rubyrep sync -c ~/W/Labo/PCiEvolBiol/rr_help.conf

