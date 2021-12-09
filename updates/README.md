PCI 'updates' directory
=======================


This directory contains update scripts allowing to move
from the previous release (n-1) to the current release (n).

- update-db.sh
- update-src.sh


`update-db.sh` allows for the required update sql to be applied to the db;
changes from release (n-1) to (n) are shipped as individual `*.sql` files,
which are applied in sequence by the script.  This can yield no update when
there are no `*.sql` files in `updates/`.

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
