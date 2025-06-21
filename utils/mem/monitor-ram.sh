#!/bin/bash

while true; do
    clear
    date '+%F %T'
    free | awk '/Mem:/ {print "mem used: " int($3/$2*1000)/10 "%"}'
    echo
    echo "%mem cmd"
    ps -ax -o %mem,cmd | sort -k1nr | head -30
    sleep 10
done
