#!/bin/bash

curl -s 'https://compstat.peercommunityin.org/api/all/issn' |\
jq -r 'to_entries[] | [.value.issn, .key ] | @tsv '
