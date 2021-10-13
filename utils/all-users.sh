#!/bin/bash

usage() {
    echo "$(basename "$0") [users|reviewers|recommenders]"
}

get_counts() {
    for pci in $(./all-pci-db.sh); do
        printf "%-30s %4d\n" \
            $pci $(./get_reviewers.sh $kind $pci | sed 1d | wc -l)
    done
}

kind=$1

case $kind in
    ""|-h|--help)
        usage
        ;;
    users|reviewers|recommenders)
        get_counts
        ;;
    *)
        echo "unknown kind: $kind"
        exit 1
        ;;
esac
