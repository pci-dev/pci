#!/bin/bash

main() {
    parse_args "$@"
}

mem_watch_reset() {
    while true; do
        mem_use=$(free | awk '/Mem:/ {print int($3/$2*100)}')

        [ $mem_use -ge $max_percent ] && {
            touch /var/www/peercommunityin/web2py/wsgihandler.py

            echo "$(date '+%F %T'): reload (mem_use=$mem_use)"
            preload

        } &>> $0.log

        sleep ${interval:-30s}
    done
}

preload() {
    curl -s https://api.peercommunityin.org/all/pci \
    | jq -r 'keys[]' \
    | while read pci; do
        curl -s https://$pci.peercommunityin.org/ >/dev/null &
    done
    wait
}

parse_args() {
    case $1 in
        -m|--max-mem) # [% use] (default: 70)
            max_percent=${2:-70}
            mem_watch_reset
            ;;
        -p|--preload) #
            preload
            ;;
        -h|--help|"")
            echo "usage: $0 [command]"
            echo
            show_opts
            ;;
        *)
            echo "unknown command: $1"
            $0 --help
            exit 1
            ;;
    esac
}

show_opts() {
    sed '1,/^parse_args/ d; /^}/,$ d' $0 \
    | grep ') #' | sed 's/) #//'
}

main "$@"
