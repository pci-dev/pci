#!/bin/bash

watch_mem() {
    date '+%F %T'
    free | awk '/Mem:/ {print "mem used: " int($3/$2*1000)/10 "%"}'
    echo
    echo "%mem cmd"
    ps -ax -o %mem,cmd,lstart | sort -k1nr | head -30
}

while true; do
    clear
    watch_mem | tee $0.log
    sleep 10
done
