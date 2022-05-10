#!/bin/bash

BASE=/var/www/peercommunityin/
PCI=$(basename $(cd $(dirname "$0")/..; pwd))
[ -d web2py ] && BASE=.

cd $BASE/web2py
python3 web2py.py --no_banner -M -S $PCI -R applications/$PCI/utils/delete_old_accounts.py
