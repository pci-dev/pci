#!/bin/bash

(set +m

for pci in $(curl -sL api.peercommunityin.org/coar_inboxes \
		| jq -r '. | keys | @tsv');
do
       curl -sL --head $pci.peercommunityin.org | grep "ldp#inbox" &
done

wait

) | sort
