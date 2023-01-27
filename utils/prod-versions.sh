#!/bin/bash

curl -s 'https://compstat.peercommunityin.org/api/all/version' |\
jq -r 'to_entries[] | [.value.version.tag[5:], .key ] | @tsv '
