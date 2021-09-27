PCI 'updates' directory
=======================


This directory contains update scripts allowing to move
from the previous release (n-1) to the current release (n).

- update-db.sh
- update-src.sh


`update-db.sh` contains the required sql to update the db from release (n-1) to (n).
The script can contain no sql if there are no changes to apply.

The git history provides for previous versions upgrade scripts.

`update-src.sh` contains basic git commands to update the source.
The script can be used to perform any required additional local updates
e.g. to configuration files which are not version-controlled.

The script also performs a web2py/wsgihandler.py reload.


Updating a PCI instance
-----------------------

	git fetch
	git checkout <version> updates
	updates/update-db.sh
	updates/update-src.sh
