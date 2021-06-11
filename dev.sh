#!/bin/bash

OPTIONS="--rm -it"

case $1 in
	-d|--daemon)
		OPTIONS="$OPTIONS -d"
		shift
		;;
	-h|--help)
		echo "usage: $(basename $0) [-d|--daemon] [commands]"
		exit 0
		;;
esac

set -x

docker image inspect pci:latest &> /dev/null || {
	docker build -t pci .
}

docker run $OPTIONS -p 8000:8000 -v "$PWD:/pci" pci "$@"
