#!/bin/bash -x

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
	-sshargs -C  \
	~/W/web2py/applications/pcidev   ssh://www-data@gaia2//home/www-data/web2py/applications/PCiEvolBiol

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


exit
