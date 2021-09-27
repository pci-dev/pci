#!/bin/bash

DB=$1

[ "$DB" ] || { echo "usage: $(basename "$0") <database>"; exit 1; }

# all_pci=$(grep psyco /var/www/peercommunityin/web2py/applications/PCI*/private/appconfig.ini | sed s:.*/::)


update() {
psql -h mydb1 -p 33648 -U peercom $DB << EOF
-- 21/09/2021
ALTER TABLE t_articles DISABLE TRIGGER auto_last_status_change_trigger;
ALTER TABLE t_articles DISABLE TRIGGER distinct_words_trigger;

ALTER TABLE t_articles ADD COLUMN IF NOT EXISTS has_manager_in_authors BOOLEAN DEFAULT false;

ALTER TABLE t_articles ENABLE TRIGGER auto_last_status_change_trigger;
ALTER TABLE t_articles ENABLE TRIGGER distinct_words_trigger;
EOF
}

update_rr() {
psql -h mydb1 -p 33648 -U peercom $DB << EOF
EOF
}

#update_rr
update
