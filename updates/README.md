PCI 'updates' directory
=======================


This directory contains update scripts allowing to move
from the previous release (n-1) to the current release (n).

- update-db.sh
- run-scripts.sh


`update-db.sh` allows for the required update sql to be applied to the db;
changes from release (n-1) to (n) are shipped as individual `*.sql` files,
which are applied in sequence by the script.  This can yield no update when
there are no `*.sql` files in `updates/`.

The git history provides for previous versions upgrade scripts.

`run-scripts.sh` runs available python scripts as web2py jobs.
The web2py scripts may perform any required update tasks, including
local files or db updates.

Option --reload performs a web2py reload (touch web2py/wsgihandler.py)


Updating a PCI instance
-----------------------

	git fetch
	git checkout <version> updates
	updates/update-db.sh --local-dir
	git merge
	updates/run-scripts.sh --all
	updates/run-scripts.sh --reload
