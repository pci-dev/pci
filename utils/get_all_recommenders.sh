#!/bin/bash

get_all() {
	../all-pci-db.sh | (
	while read pci; do
		../get_users.sh $cmd $pci > $pci.$out &
	done
	wait
	)

	wc -l *.$out
	cat *.$out | sort -u > all_$out
}

out=reco-2016-now.csv
cmd=recommenders2
get_all

out=reco-2022-now.csv
cmd=new_recommenders
get_all
