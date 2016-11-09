#!/bin/bash

find . -name \*.py -ls -exec sed -i~ -e 's/AppConfig(reload=True)/AppConfig(reload=False)/; s/track_changes(True)/track_changes(False)/' {} \;

