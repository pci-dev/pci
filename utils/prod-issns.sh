#!/bin/bash

curl -s 'https://api.peercommunityin.org/all/issn' |\
jq -r 'to_entries[] | [.value.issn, .key ] | @tsv '
