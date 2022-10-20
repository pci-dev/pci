# PCIDEV : Peer Community website dev

## A free recommendation process of published and unpublished scientific papers based on peer reviews

---

## What is PCI ?

The “Peer Community in” project is a non-profit scientific organization aimed at creating specific communities of researchers reviewing and recommending papers in their field. These specific communities are entitled Peer Community in X, e.g. Peer Community in Evolutionary Biology, Peer Community in Microbiology.

---

## Install project

Requirements: Python (3.8 or greater), PostgreSql (9.6 or greater), web2py.

Additional requirements: libimage-exiftool-perl, ghostscript (9.26+)

Suggestion: use a python virtual env

	sudo apt-get install virtualenvwrapper
	mkvirtualenv pci --python=`which python3.8`


Install all required components:

	make install

Give yourself postgres admin access

	make db.admin

Create PostgreSql database and user

	make db


Run the PCI server:

	make start

creates default config file:
- `private/appconfig.ini`







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


Docker container
----------------

PCI can run as a docker container.

See [doc / Docker](doc/Docker-container.md).


File structure
--------------

PCI is a `web2py` application, with a standard web2py file structure.

See [doc / File structure](doc/File-structure.md) for details.


COAR Notify
-----------

PCI contains a COAR Notify implementation.

See [doc / COAR Notify](doc/COAR-Notify.md).
