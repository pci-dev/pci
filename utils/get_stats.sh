#!/bin/bash


main() {
    case $1 in
        ""|-h|--help)
            commands() { awk '/# commands$/ {print $1}' $0; }
            echo "usage: $(basename $0) <$(commands)> <pci_xxx>"
            exit 0
            ;;
        articles|reviews ) # commands
            ;;
        *)
            echo "unknown command: $1"
            exit 1
            ;;
    esac
    case $2 in
        pci_*)
            DB=$2
            ;;
        *)
            echo "invalid db: '$2'"
            exit 2
            ;;
    esac

    get_$1 | db_output_adapter
}

get_articles() {
    _psql <<< "
    select status, count(*) from t_articles group by status;
    "
}

get_reviews() {
    _psql <<< "
    select review_state, count(*) from t_reviews group by review_state;
    "
}

db_output_adapter() {
    sed '$d;1,2d' | sed '$d' | tr -s " " | sort
}

_psql() {
    psql -h mydb1 -p 33648 -U peercom $DB
}

main "$@"
