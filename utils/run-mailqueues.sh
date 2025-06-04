#!/bin/bash

BASE=/var/www/peercommunityin/web2py/applications
RUN=cron_tasks/run


run_mailqueues() {
    run_start=$(date +%s)
    with_newsletter=$((nb++ % 5))

    echo "* RUN START $(date +'%D %T')"
    [ $with_newsletter = 1 ] && echo "(with newsletter)"

    for SITE in $(cd $BASE; ls | egrep 'PCI|TEST'); do
        job_start=$(date +%s)
        printf "%-32s" "$SITE"

        $BASE/$SITE/$RUN mail_queue.py
        [ $with_newsletter = 1 ] && {
            $BASE/$SITE/$RUN newsletter.py
        }

        echo "[$(sec_from $job_start)]"
    done

    echo "* RUN DONE in $(sec_from $run_start)"
}

sec_from() {
    start=$1
    now=$(date +%s)
    echo "$((now-start))s"
}

sleep_until() {
    duration=$(( $1 - `date +%s`))
    [ $duration -gt 0 ] && sleep $duration
}

main() {
    while true; do
        run_mailqueues
        sleep_until $((run_start + 60))
    done
}

check_running() {
    pid=$(ps -C `basename $0` -o pid=)
    pid=$(ps -o pid= $pid | grep -v $$)
    [ "$pid" = "" ] || {
        echo already running:
        ps $pid
        exit 1
    }
}

case $1 in
    -d|--daemon)
        check_running
        main &>> $0.log &
        ;;
    -r|--run)
        check_running
        run_mailqueues | tee -a $0.log
        ;;
    -c|--check)
        check_running
        echo "not running"
        ;;
    -h|--help|"")
        echo "usage: $0 [-d|--daemon] [-r|--run] [-c|--check]"
        ;;
    *)
        echo "unknown command: $1"
        exit 1
        ;;
esac
