#!/bin/bash

all_pci=$(./all-pci-db.sh)

set_data_dir() {
    data_dir=data/$WHAT
}

get_stats() {
    mkdir -p $data_dir

    for pci in $all_pci; do
        ./get_stats.sh $WHAT $pci > $data_dir/$pci.txt &
    done
    wait
}

mk_table() {
    (cd $data_dir

    categories=cat
    cat *.txt | cut -d '|' -f 1 | sort -u > $categories

    for pci in *.txt; do
        join -a 1 -a 2 -t '|' -o 2.2 $categories $pci > $pci.col &
    done
    wait

    paste $categories *.col
    rm $categories *.col
    )
}

mk_header() {
    ls $data_dir | sed 's/pci_//; s/\.txt//' | xargs | tr ' ' '\t'
}

tabulate() {
    printf "$WHAT\t" | tr '[a-z]' '[A-Z]'
    mk_header
    mk_table
}

main() {
    for WHAT in articles reviews; do
        set_data_dir
        get_stats
        tabulate | tee pci.$WHAT.tsv
        echo
    done
}

main
