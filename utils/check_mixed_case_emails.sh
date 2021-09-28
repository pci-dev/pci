#!/bin/bash

cd accounts
ls *.users.txt | sed 's:\..*::' | while read f ; do
        diff -u $f.users.txt.sorted $f.users.lower.txt.sorted
        echo -

done | egrep '^-' | grep -v email
