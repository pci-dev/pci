#!/bin/bash

SITES=$(dirname $0)/sites

PILOTS='TEST|Zool|EvolBiol|Reports'

RELEASE=${release:-origin/master}
#RELEASE=origin/development


main() {
    case $1 in
        pilots | others) #
            update_$1
            ;;
        pci) # [site] [egrep expr]...
            shift
            update $*
            ;;
        ""|-h|--help)#
            usage
            ;;
        *)#
            echo "unknow command: $1"
            usage
            exit 1
            ;;
    esac
}

usage() {
    echo "usage: $0 [command]"
    cat $0 | sed '/^usage()/,$ d' | egrep "^ .*)[^#]" | tr -d ')#'
}

update_pilots() {
    update "$PILOTS"
}

update_others() {
    update $(ls $SITES | grep PCI | egrep -v "$PILOTS")
}

update() {
    (cd $SITES

    spec=$(echo $* | tr ' ' '|')
    sites=$(ls | egrep -i "$spec" | egrep 'PCI|TEST')

    [ "$spec"  ] || { echo "no site specified"; return 1; }
    [ "$sites" ] || { echo "no such sites: $spec"; return 1; }

    for pci in $sites; do
        echo "$pci.update"
        (
        cd $pci
        echo === $pci ===

        git fetch --prune
        update_db
        git merge $RELEASE

        ) &> ~/updates/$pci.update &
    done
    wait

    cd TEST
    make reload.web2py
    utils/prod-versions.sh

    )
}


update_db() {
    rm -rf updates/
    git checkout $RELEASE updates
    updates/update-db.sh --local-dir
    rm -rf updates/
    git checkout updates/
}

update_reminders() {
    diff -u private/sample.appconfig.ini private/appconfig.ini
    set -x
    touch modules/app_modules/reminders.py
}

main "$@"
