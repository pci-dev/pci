#!/bin/bash

# unison -auto -ignore "Name *.pyc" -ignore "Name .git" -ignore "Name sessions" -ignore "Name errors" -sshargs -C  ~/W/web2py/applications/pcidev   ssh://piry@gaia2//home/www-data/web2py/applications/PCiEvolBiol

unison -auto -ignore "Name appconfig.ini" -ignore "Name crontab" -ignore "Name *~" -ignore "Name *.pyc" -ignore "Name .git" -ignore "Name sessions" -ignore "Name errors" -sshargs -C  ~/W/web2py/applications/pcidev   ssh://www-data@gaia2//home/www-data/web2py/applications/PCiEvolBiol


