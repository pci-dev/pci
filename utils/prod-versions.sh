#!/bin/bash

curl -s 'https://api.peercommunityin.org/all/version' |\
jq -r 'to_entries[] | [.value.version.tag, .key ] | @tsv '
