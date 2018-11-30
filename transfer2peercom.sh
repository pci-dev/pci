#!/bin/bash -x

src_name="/home/piry/W/web2py_2.17.2/applications/pcidev/"
dir_name="/var/www/peercommunityin/web2py217/applications/PCIEvolBiol"
db_name="pci_evolbiol"
rsopts="--verbose --progress --times --usermap=peercom:www-data"

datam="static/images/RSS_datamatrix.png"
echo "https://evolbiol.peercommunityin.org/public/rss" | dmtxwrite --encoding=b --module=4 --output=$datam


# # TRANSFER HELP TABLE  gaia2 --> peercom
# pg_dump  -h gaia2 -p 5432 -U piry -F p --data-only --table=help_texts pci_evolbiol_test > helpTexts_of_gaia2.sql
# echo "TRUNCATE help_texts;"   | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat helpTexts_of_gaia2.sql    | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

# Data changes ---> Shit; deactivate trigger bofore!!
# echo "UPDATE t_reviews SET review_state='Completed' WHERE review_state LIKE 'Terminated';" | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

# SYNC SOURCE CODE FROM MBIPI TO WEBSITE
rsync $rsopts --stats --recursive --perms --links --update --delete --delete-before --exclude='*~' --exclude='*.pyc' --exclude='*.bak' --exclude '.git' --exclude 'sessions' --exclude 'cache' --exclude 'errors' --exclude '*.ini' --exclude '*.old' --exclude '*background.png' --exclude '*workflow*.png' $src_name peercom@peercom-front1:$dir_name

# cat /home/piry/W/Labo/PCiEvolBiol/2017-09-18_modifs_fonctions.sql                                  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-13_auto_last_change_recommendation_trigger_function.sql  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-27_search_recommenders.sql                               | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-29_search_reviewers.sql                                  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-12-06_resources.sql                                         | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-12-08_search_recommenders.sql                               | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2017-12-14_trigger_reviews.sql                                   | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2018-01-26_search_reviewers.sql  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2018-01-26_versionMS.sql                                  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# echo "UPDATE help_texts SET contents = regexp_replace(contents, 'font-family *: *optima *;', '', 'ig') WHERE contents ~* 'font-family *: *optima *;';"  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2018-03-09_colpivot.sql                                  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# echo "UPDATE help_texts SET contents='Code of conduct' WHERE hashtag LIKE '#EthicsTitle';"  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# echo "ALTER TABLE public.auth_user ALTER COLUMN alerts SET DEFAULT '||'::character varying;"  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# echo "ALTER TABLE public.t_articles ADD COLUMN anonymous_submission boolean DEFAULT false;"  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# echo "ALTER TABLE public.t_articles ADD COLUMN cover_letter text;"  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# cat /home/piry/W/Labo/PCiEvolBiol/2018-07-23_auto_last_change_recommendation_trigger_function.sql  | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# echo "ALTER TABLE public.t_recommendations ADD COLUMN recommender_file character varying(512); ALTER TABLE public.t_recommendations ADD COLUMN recommender_file_data bytea;" | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"
# echo "ALTER TABLE public.t_suggested_recommenders ADD COLUMN emailing text;" | ssh peercom@peercom-front1 "psql -h mydb1 -p 5432 -U peercom -d $db_name"

#WARNING: check group!!
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/private/peercom_appconfig.ini            peercom@peercom-front1:$dir_name/private/appconfig.ini
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/background.png             peercom@peercom-front1:$dir_name/static/images
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/small-background.png       peercom@peercom-front1:$dir_name/static/images
# rsync $rsopt /home/piry/W/web2py/applications/pcidev/static/images/workflow1.png              peercom@peercom-front1:$dir_name/static/images

ssh peercom@peercom-front1 "chgrp www-data $dir_name/private/appconfig.ini ; chmod 640 $dir_name/private/appconfig.ini ; find $dir_name -name \\*.pyc -ls ; find $dir_name -name \\*.pyc -exec rm {} \\; ; touch $dir_name/../wsgihandler.py"

echo "http://localhost:8000/pcidev/public/rss" | dmtxwrite --encoding=b --module=4 --output=$datam

