#!/bin/sh -e

set -x

sudo -u postgres pg_ctl start -w -D $PGDATA
nginx
/web2py/web2py.py --password $PCI_PASSWORD -p 8001
