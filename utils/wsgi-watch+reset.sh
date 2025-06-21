#!/bin/bash


PCIs=$(curl -s https://api.peercommunityin.org/all/pci | jq -r 'keys[]')


watch_and_reset() {
    for pci in $PCIs; do
        curl -s https://$pci.peercommunityin.org/ > /tmp/watch.$pci &
    done
    wait

    for pci in $PCIs; do
        grep -q pci-home /tmp/watch.$pci || {

            echo "`date +'%F %T'`: resetting $pci (down)"
            kill_wsgi $pci
        }
    done
}

kill_wsgi() {
    animsci=wsgi:web2pyanims
    archaeo=wsgi:web2pyarcha
    ecology=wsgi:web2pyecolo
    ecotoxenvchem=wsgi:web2pyecoto
    evolbiol=wsgi:web2pyevolb
    forestwoodsci=wsgi:web2pyfores
    genomics=wsgi:web2pygenom
    healthmovsci=wsgi:web2pyhealt
    infections=wsgi:web2pyinfec
    mcb=wsgi:web2pymcb
    microbiol=wsgi:web2pymicro
    networksci=wsgi:web2pynetwo
    neuro=wsgi:web2pyneuro
    nutrition=wsgi:web2pynutri
    orgstudies=wsgi:web2pyorgst
    paleo=wsgi:web2pypaleo
    plants=wsgi:web2pyplant
    psych=wsgi:web2pypsych
    rr=wsgi:web2pyrr
    zool=wsgi:web2pyzool

    pci=$1
    pid=$(ps -ax -o pid,cmd | grep ${!pci} | grep -v grep | cut -d ' ' -f 1)
    sudo -u www-data kill $pid
}

main() {
    while true; do
        watch_and_reset &>> $0.log
        sleep 42
    done
}

main
