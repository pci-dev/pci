PCI - Peer Community In
=======================

Free recommendation process for published and unpublished scientific papers
based on peer reviews


What is PCI ?
-------------

The “Peer Community in” project is a non-profit scientific organization aimed at creating specific communities of researchers reviewing and recommending papers in their field. These specific communities are entitled Peer Community in X, e.g. Peer Community in Evolutionary Biology, Peer Community in Microbiology.


Installing from source
----------------------

Requirements:

- python (3.8+), postgreSql (9.6+), web2py
- libimage-exiftool-perl, ghostscript (9.26+)


Suggestion: use a python virtual env

	sudo apt-get install virtualenvwrapper
	mkvirtualenv pci --python=`which python3.8`


Install, configure, run:

	make install    # install all required components

	make db.admin   # give yourself postgres admin access

	make db         # create PostgreSql database and user

	make start      # run the PCI server


Browse the "empty" PCI at http://localhost:8000/pci

The instance above runs with no mail server configured, which is ok for dev.

In a prod setup, mails are sent by the mailing queue, run as a cronjob.

See [doc / Mailing-queue](doc/Mailing-queue.md) to run one.


Running tests
-------------

There are currently two flavours of automated tests:
- cypress
- selenium+pytest

The tests can be used to populate an "empty" vanilla dev instance.

See [doc / Tests setup](doc/Tests-setup.md) then use:

	make test.reset
	make test.basic
	make test.full


Further reading
---------------

- [doc / File structure](doc/File-structure.md)
- [doc / COAR Notify](doc/COAR-Notify.md)
- [doc / Docker](doc/Docker-container.md)
