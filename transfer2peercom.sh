#!/bin/bash -x

dir_name="/var/www/peercommunityin/web2py/applications/PCIEvolBiol"
db_name="pci_evolbiol"
rsopts="--verbose --progress --times --usermap=peercom:www-data"

# # TRANSFER HELP TABLE  gaia2 --> peercom
# pg_dump  -h gaia2 -p 5432 -U piry -F p --data-only --table=help_texts pci_evolbiol_test > helpTexts_of_gaia2.sql
# echo "TRUNCATE help_texts;"   | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat helpTexts_of_gaia2.sql    | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

# Data changes
# echo "UPDATE t_reviews SET review_state='Completed' WHERE review_state LIKE 'Terminated';" | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"


# SYNC SOURCE CODE FROM MBIPI TO WEBSITE
rsync $rsopts --stats --recursive --perms --links --update --delete --delete-before --exclude='*~' --exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' --exclude 'errors' --exclude '*.ini' --exclude '*.old' --exclude '*background.png' --exclude '*workflow*.png' ~/W/web2py/applications/pcidev/ peercom@peercom-front1:$dir_name

# cat /home/piry/W/Labo/PCiEvolBiol/2017-09-18_modifs_fonctions.sql                                  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-13_auto_last_change_recommendation_trigger_function.sql  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-27_search_recommenders.sql                               | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-29_search_reviewers.sql                                  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

#TODO cat /home/piry/W/Labo/PCiEvolBiol/2017-12-06_resources.sql                                  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

#WARNING: check group!!
rsync $rsopt /home/piry/W/web2py/applications/pcidev/private/peercom_appconfig.ini            peercom@peercom-front1:$dir_name/private/appconfig.ini
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/background.png             peercom@peercom-front1:$dir_name/static/images
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/small-background.png       peercom@peercom-front1:$dir_name/static/images
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/workflow1.png              peercom@peercom-front1:$dir_name/static/images

ssh peercom@peercom-front1 "chgrp www-data $dir_name/private/appconfig.ini ; chmod 640 $dir_name/private/appconfig.ini ; find $dir_name -name \\*.pyc -ls ; find $dir_name -name \\*.pyc -exec rm {} \\; ; touch /var/www/peercommunityin/web2py/wsgihandler.py"

# exit

