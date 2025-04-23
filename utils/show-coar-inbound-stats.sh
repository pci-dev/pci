./all-pci-db.sh | grep -v compstat | while read pci; do
        printf "%d\t $pci\n" $( (db=$pci; psql -t -h mydb1 -p 33648 -U peercom $db) \
        <<< "select count(id) from t_coar_notification where direction = 'Inbound'; ")
done
