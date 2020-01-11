#!/bin/bash

find . -name \*.py -ls -exec sed -i~ -e 's/AppConfig(reload=False)/AppConfig(reload=True)/; s/track_changes(False)/track_changes(True)/' {} \;

