zgrep "POST /coar_notify/inbox" /var/log/apache2/*_access.log* \
| awk '{print $4, $5, $9, $1, $12}' \
| sed 's,/var/log/apache2/,,' \
| sed 's,_access.*:, ,' \
| grep -v compstat \
| sort
