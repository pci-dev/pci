#!/bin/bash -x

# Compatibility with web redirection by www1.supagro.inra.fr/PCI/: 
# In order to rewrite generated URLs with a leading /PCI/
# and to accept incoming URLs by removing this leading /PCI/,
# check routes.py file in web2py dir:
#
# routes_in =((r'^/PCI/(?P<any>.*)', r'/\g<any>'),)
# routes_out=((r'^/(?P<any>.*)', r'/PCI/\g<any>'),)


# 0/ Define shell variables :
pcirep="/home/piry/W/Labo/PCi_other"
srcrep="/home/piry/W/web2py_2.20.4/applications/PciGabGit"
app="PCiInfections"
server="pci-test3"
apprep="/home/www-data/web2py_2.20.4/applications/$app"
ip="147.99.64.107"
database="pci_infections"
name="PCIInfections"
longname="PCI Infections"
description="Peer Community In Infections"
thematics="Infections"
issn="PENDING"
contact=
manager=$contact
twitter=PCI_Infections
servername="www1.montpellier.inra.fr"
serverscheme="https"
serverport=443

DB_AUTH= # user:password

SMTP_SERVER=ssl0.ovh.net:465
SMTP_USER=dev@peercommunityin.org
SMTP_PASS=

CAPTCHA_PUB=
CAPTCHA_PRIV=


# 1/ Clean (if any) then (re-)create database:
echo "DROP DATABASE IF EXISTS $database;" | psql -h $ip postgres
echo "CREATE DATABASE $database;" | psql -h $ip postgres

# 2/ Copy current db structure from EvolBiol to the new db:
pg_dump -h $ip -F p -N work -s -O -d pci_evolbiol_test | psql -h $ip $database

# 3a/ Reset linked table contents and add myself with all roles
psql -h $ip $database << EOF
TRUNCATE auth_user, auth_group CASCADE;
INSERT INTO auth_user ("id", "first_name", "last_name", "email", "password", "registration_key", "reset_password_key", "registration_id", "picture_data", "uploaded_picture", "user_title", "city", "country", "laboratory", "institution", "alerts", "thematics", "cv", "last_alert", "registration_datetime", "ethical_code_approved") VALUES (1, 'Sylvain', 'Piry', 'sylvain.piry@inrae.fr',  'pbkdf2(1000,20,sha512)$a8aeb4e0f35fd57b$43d7678c72a6ed83841beb894006e7a793dd78a1', '', '', '', NULL, NULL, 'M.', 'Montpellier', 'France', 'CBGP', 'INRA', '||', '||', '', NULL, '2016-11-03 13:17:38', TRUE);
INSERT INTO public.auth_group (id, role, description) VALUES (2, 'recommender', '');
INSERT INTO public.auth_group (id, role, description) VALUES (3, 'manager', '');
INSERT INTO public.auth_group (id, role, description) VALUES (4, 'administrator', '');
INSERT INTO public.auth_group (id, role, description) VALUES (5, 'developer', '');
SELECT pg_catalog.setval('public.auth_group_id_seq', 7, true);
SELECT setval('public.auth_user_id_seq', 2, true);
INSERT INTO auth_membership (user_id, group_id) SELECT 1, id FROM auth_group;
INSERT INTO t_thematics (keyword) VALUES ('TEST');
EOF

# 3b/ Transfer help texts, article status,... 
echo "TRUNCATE public.help_texts;" | psql -h $ip $database
pg_dump -h $ip -F p -O -d pci_evolbiol_test -t public.help_texts -a --inserts --column-inserts \
	| psql -h $ip $database
echo "TRUNCATE public.t_status_article CASCADE;" | psql -h $ip $database
pg_dump -h $ip -F p -O -d pci_evolbiol_test -t public.t_status_article -a --inserts --column-inserts \
	| psql -h $ip $database
# NOTE dump le mail_templates de EvolBiolTest3
echo "TRUNCATE mail_templates;"   | psql -h $ip $database
pg_dump --host=$ip --table=mail_templates --data-only pci_evolbiol_test | psql -h $ip $database
echo "SELECT pg_catalog.setval('public.mail_templates_id_seq', (SELECT max(id)+1 FROM mail_templates), true);" | psql -h $ip $database

# 4/ Create configuration file (using variables)
mkdir -p $pcirep/$app
cat > $pcirep/$app/appconfig_test.ini << EOF
; App configuration
[app]
name        = $name
longname    = $longname
author      = Sylvain Piry <sylvain.piry@inra.fr>
description = $description
thematics   = $thematics
generator   = Web2py Web Framework
issn        = $issn

; Host configuration
[host]
names = localhost:*, 127.0.0.1:*, *:*, *

; db configuration
[db]
uri       = postgres:psycopg2://$DB_AUTH@$ip:5432/$database
migrate   = false
pool_size = 100

; smtp address and credentials
[smtp]
server = $SMTP_SERVER
sender = PCI Development <$SMTP_USER>
login = $SMTP_USER:$SMTP_PASS
tls = true
ssl = true

; form styling
[forms]
formstyle = bootstrap3_inline
separator =

; custom data
[contacts]
contact = $contact
managers = $manager

[config]
trgm_limit = 0.4 
parallel_submission = False
review_due_time_for_parallel_submission = "30 days"
review_due_time_for_exclusive_submission = "two weeks"
tracking = False
unconsider_limit_days = 20
review_limit_days = 20
recomm_limit_days = 50
pdf_max_size = 5
mail_delay = 3
mail_queue_interval = 15
mail_max_sending_attemps = 3
[rss]
cache  = 60
number = 20

[alerts]
scheme = $serverscheme
host = $servername
port = $serverport
delay = 10

[captcha]
public = $CAPTCHA_PUB
private = $CAPTCHA_PRIV

[social]
tweeter = $twitter
tweethash = $twitter
EOF

# 5/ Background files (or manually install true ones) & other images
cp $pcirep/tmp_small-background.png $pcirep/$app/small-background.png 
cp $pcirep/tmp_background.png $pcirep/$app/background.png 
cp $pcirep/Workflow20180314.png $pcirep/$app/Workflow20180314.png

# 6/ Create synchronization file
cat > $pcirep/$app/syncTest.sh << EOF
#!/bin/bash -x
unison -auto \
	-ignore "Name *.ini" \
	-ignore "Name crontab" \
	-ignore "Name *~" \
	-ignore "Name *.bak" \
	-ignore "Name *.pyc" \
	-ignore "Name *.orig" \
	-ignore "Name .git" \
	-ignore "Name sessions" \
	-ignore "Name tmp" \
	-ignore "Name errors" \
	-ignore "Name *background*.png" \
	-ignore "Name favicon.*" \
	-ignore "Name *datamatrix.*" \
	-sshargs -C $srcrep ssh://www-data@$server/$apprep

ssh www-data@$server "chmod 775 $apprep ; mkdir -p -m 775 $apprep/uploads ; mkdir -p -m 775 $apprep/sessions ; mkdir -p -m 775 $apprep/errors ; chgrp -R www-data $apprep ; find $apprep -type d -exec chmod g+rwx {} \\;"

echo "$serverscheme://$servername:$serverport/$app/rss/rss" \
	| dmtxwrite --encoding=b --module=4 --output=$pcirep/$app/RSS_datamatrix.png
rsync --times $pcirep/$app/appconfig_test.ini   www-data@$server:$apprep/private/appconfig.ini
rsync --times --copy-links $pcirep/$app/background.png         www-data@$server:$apprep/static/images
rsync --times --copy-links $pcirep/$app/small-background.png   www-data@$server:$apprep/static/images
rsync --times --copy-links $pcirep/favicon.*                   www-data@$server:$apprep/static/images
rsync --times --copy-links $pcirep/$app/RSS_datamatrix.png     www-data@$server:$apprep/static/images

ssh www-data@$server "find $apprep -name \\*.pyc -exec rm {} \\; ; touch $apprep/../../wsgihandler.py"
EOF


# 7/ Run the synchronization
chmod 750 $pcirep/$app/syncTest.sh
cd $pcirep/$app
sh ./syncTest.sh

# 8/ It (should) work!
# Test access from https://www1.montpellier.inra.fr/PCI/PCiInfections/
