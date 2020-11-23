#!/bin/bash -x

src_name="/home/piry/W/web2py_2.17.2/applications/pci_stable/"
dir_name="/var/www/peercommunityin/web2py217/applications/PCIEvolBiol"
db_name="pci_evolbiol"
db_test="pci_evolbiol_test"
ip="mydb1"
db=$db_name

rsopts="--verbose --progress --times --usermap=peercom:www-data"

datam="static/images/RSS_datamatrix.png"
echo "https://evolbiol.peercommunityin.org/public/rss" | dmtxwrite --encoding=b --module=4 --output=$datam

# # TRANSFER HELP TABLE  gaia2 --> peercom
# pg_dump  -h gaia2 -p 5432 -U piry -F p --data-only --table=help_texts pci_evolbiol_test > helpTexts_of_gaia2.sql
# echo "TRUNCATE help_texts;"   | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat helpTexts_of_gaia2.sql    | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

# Data changes ---> Shit; deactivate trigger bofore!!
# echo "UPDATE t_reviews SET review_state='Review completed' WHERE review_state LIKE 'Terminated';" | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

# SYNC SOURCE CODE FROM MBIPI TO WEBSITE
rsync $rsopts --stats --recursive --perms --links --update --delete --delete-before --exclude='*~' \
	--exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' \
	--exclude 'errors' --exclude '*.ini' --exclude '*.old' --exclude '*background.png' --exclude '*workflow*.png' \
	$src_name \
	peercom@peercom-front1:$dir_name


#WARNING: check group!!
rsync $rsopt /home/piry/W/web2py/applications/pcidev/private/peercom_appconfig.ini            peercom@peercom-front1:$dir_name/private/appconfig.ini
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/background.png             peercom@peercom-front1:$dir_name/static/images
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/small-background.png       peercom@peercom-front1:$dir_name/static/images
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/workflow1.png              peercom@peercom-front1:$dir_name/static/images
# rsync $rsopt /home/piry/W/Labo/PCiEvolBiol/sponsors_banner.png                                peercom@peercom-front1:$dir_name/static/images

ssh peercom@peercom-front1 "chgrp www-data $dir_name/private/appconfig.ini ; chmod 640 $dir_name/private/appconfig.ini ; find $dir_name -name \\*.pyc -ls ; find $dir_name -name \\*.pyc -exec rm {} \\; ; touch $dir_name/../wsgihandler.py"

echo "http://localhost:8000/pcidev/public/rss" | dmtxwrite --encoding=b --module=4 --output=$datam

# # WARNING: rapatrie les help officiels vers le test local
# ssh peercom@peercom-front1 "pg_dump -h mydb1 -p 5432 -U peercom -d $db_name --format=plain --data-only --table=help_texts" > helpTextsOfficiels.sql
# echo "TRUNCATE help_texts;" | psql -h cbgp-pci-test.supagro.inra.fr -U piry $db_test 
# cat helpTextsOfficiels.sql  | psql -h cbgp-pci-test.supagro.inra.fr -U piry $db_test 
# rm helpTextsOfficiels.sql

