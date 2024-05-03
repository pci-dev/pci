#!/bin/bash -x

log="$0.log"
dir="${0%/*}"

python -m pyftpdlib \
    -i 127.0.0.1 \
    -p 2100 \
    -u clockss \
    -P the_clockss_passwd \
    -d $dir \
    --write \
    &> $log	|| pip install pyftpdlib
