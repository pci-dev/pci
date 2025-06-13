#!/bin/bash

while true; do
    clear
    date '+%F %T'
    echo "%mem cmd"
    ps -ax -o %mem,cmd | sort -k1nr | head -30
    sleep 10
done
