./all-pci-db.sh | grep -v compstat | while read pci ; do
        (db=$pci; psql -t -h mydb1 -p 33648 -U peercom $db) <<EOT
        select  id,
                created,
                '$pci' as pci,
                substring(body from '"name": "[^"]*"') as name,
                substring(body from '"mailto:[^"]*"') as email,
                substring(body from '"ietf:cite-as": "[^"]*"') as doi

        from t_coar_notification

        where direction = 'Inbound'
        and coar_id not in (
                select coar_notification_id from t_articles
                where coar_notification_id is not null
        )
        order by id;
EOT

  done | sed '
  s/"name": "//; s/"//;
  s/"mailto://; s/"//;
  s/"ietf:cite-as": "//; s/"//;
  s/ | /\t/g
  '
