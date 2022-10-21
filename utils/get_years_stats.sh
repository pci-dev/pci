#!/bin/bash

submissions_by_year() {
    echo "
    select extract (year from $date_field) as year, count(id)
    from t_articles
    group by year
    order by year;
    "
}

submissions_by_status() {
    echo "
    select status, extract (year from $date_field) as year, count(id)
    from t_articles
    group by year, status
    order by year desc, status
    \\crosstabview
    "
}

submissions_by_creation() {
    date_field="upload_timestamp"
}

submissions_by_decision() {
    date_field="last_status_change"
}


main() {
    parse_args "$@"

    for date in creation decision; do
            echo "==== by $date by $kind ===="
            echo

            for pci in `./all-pci-db.sh`; do
                echo $pci;
                submissions_by_$date
                submissions_by_$kind \
                | (db=$pci; psql -h mydb1 -p 33648 -U peercom $db) \
                | tr '|+' '\t'
            done
    done
}

parse_args() {
	case "$1" in
		""|--help|-h)
			echo "usage: $0 <year|status>"
			exit 0
			;;
		year|status)
			kind=$1
			;;
		*)
			echo "invalid argument: $1"
			;;
	esac
}


main "$@"
