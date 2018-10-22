#!/bin/bash -x

# RSS link as datamatrix
datam="/home/piry/Documents/Labo/PCiEvolBiol/RSS_datamatrix.png"
echo "http://147.99.65.220:82/PCiEvolBiol/public/rss" | dmtxwrite --encoding=8 --module=4 --output=$datam

# GAIA2
~/bin/unison-2.40.61 -auto \
	-ignore "Name *.old" \
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
	-ignore "Name *workflow.png" \
	-ignore "Name *datamatrix.*" \
	-ignore "Name *Map.png" \
	-sshargs -C  \
	~/W/web2py/applications/pcidev   ssh://www-data@gaia2//home/www-data/web2py/applications/PCiEvolBiol

rsopt="--verbose --progress --times"
rsync $rsopt $datam  www-data@gaia2:/home/www-data/web2py/applications/PCiPaleontology/static/images

# ssh www-data@gaia2 "find /home/www-data/web2py/applications/PCiEvolBiol -name \\*.pyc -ls ; find /home/www-data/web2py/applications/PCiEvolBiol -name \\*.pyc -exec rm {} \\; ; touch /home/www-data/web2py/wsgihandler.py"
ssh www-data@gaia2 "find /home/www-data/web2py/applications/PCiEvolBiol -name \\*.pyc -exec rm {} \\; ; touch /home/www-data/web2py/wsgihandler.py"

# echo "UPDATE t_reviews SET review_state='Completed' WHERE review_state LIKE 'Terminated';" | psql -h gaia2 -U piry pci_evolbiol
# echo "SELECT DISTINCT review_state FROM t_reviews;" | psql -h gaia2 -U piry pci_evolbiol
# echo "ALTER TABLE public.t_recommendations ADD COLUMN track_change character varying(512); ALTER TABLE public.t_recommendations ADD COLUMN track_change_data bytea;" | psql -h gaia2 -U piry pci_evolbiol
# cat ~/Documents/Labo/PCiEvolBiol/2017-09-18_modifs_fonctions.sql  | psql -h gaia2 -U piry pci_evolbiol
# cat ~/Documents/Labo/PCiEvolBiol/2017-09-26_search_reviewers.sql  | psql -h gaia2 -U piry pci_evolbiol
# echo "ALTER TABLE t_reviews ADD COLUMN acceptation_timestamp timestamp without time zone;" | psql -h gaia2 -U piry pci_evolbiol
# # # # # # # echo "ALTER TABLE t_recommendations ADD COLUMN proposed_decision varchar(50);" | psql -h gaia2 -U piry pci_evolbiol
# cat /home/piry/Documents/Labo/PCiEvolBiol/2017-09-29_Pre-status.sql  | psql -h gaia2 -U piry pci_evolbiol
# echo "ALTER TABLE public.t_reviews ADD COLUMN emailing text;" | psql -h gaia2 -U piry pci_evolbiol
# cat /home/piry/Documents/Labo/PCiEvolBiol/2017-10-05_reviewStatusFunction.sql  | psql -h gaia2 -U piry pci_evolbiol
# cat /home/piry/W/Labo/PCiEvolBiol/2017-10-11_auto_last_change_recommendation_trigger_function.sql  | psql -h gaia2 -U piry pci_evolbiol
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-13_search_recommenders.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-13_auto_last_change_recommendation_trigger_function.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-27_search_recommenders.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2017-11-29_search_reviewers.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2017-12-06_resources.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2017-12-08_search_recommenders.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2017-12-14_trigger_reviews.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2018-01-26_search_reviewers.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2018-01-26_versionMS.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# echo "UPDATE help_texts SET contents = regexp_replace(contents, 'font-family *: *optima *;', '', 'ig') WHERE contents ~* 'font-family *: *optima *;';"  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2018-03-09_colpivot.sql                                 | psql -h gaia2 -U piry pci_evolbiol_test
# echo "UPDATE help_texts SET contents='Code of conduct' WHERE hashtag LIKE '#EthicsTitle';"  | psql -h gaia2 -U piry pci_evolbiol_test
# echo "ALTER TABLE public.auth_user ALTER COLUMN alerts SET DEFAULT '||'::character varying;"  | psql -h gaia2 -U piry pci_evolbiol_test
# echo "ALTER TABLE public.t_articles ADD COLUMN anonymous_submission boolean DEFAULT false;"  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2018-07-04_SearchArticles.sql  | psql -h gaia2 -U piry pci_evolbiol
# echo "ALTER TABLE public.t_articles ADD COLUMN cover_letter text;"  | psql -h gaia2 -U piry pci_evolbiol_test
# cat /home/piry/W/Labo/PCiEvolBiol/2018-07-23_auto_last_change_recommendation_trigger_function.sql  | psql -h gaia2 -U piry pci_evolbiol_test
# echo "ALTER TABLE public.t_recommendations ADD COLUMN recommender_file character varying(512); ALTER TABLE public.t_recommendations ADD COLUMN recommender_file_data bytea;" | psql -h gaia2 -U piry pci_evolbiol_test
# echo "ALTER TABLE public.t_suggested_recommenders ADD COLUMN emailing text;" | psql -h gaia2 -U piry pci_evolbiol_test

# Delete local datamatrix
rm -f $datam
