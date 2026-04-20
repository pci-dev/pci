#! /bin/bash

SCRIPT=/home/peercom/run-mailqueues.sh

RESULT=$($SCRIPT -c)

if [ "$RESULT" = "not running" ]; then
    echo "Try to start script in deamon mode.."
	$SCRIPT -d
    echo "Ok!"
    echo "Check if script is running.."
    $SCRIPT -c || true
    exit 0
    
else
    $SCRIPT -c || true
    exit 0
fi
