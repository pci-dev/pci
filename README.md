PCI - Peer Community In
=======================

Free recommendation process for published and unpublished scientific papers
based on peer reviews

https://peercommunityin.org


What is PCI ?
-------------

The “Peer Community in” project is a non-profit scientific organization aimed at creating specific communities of researchers reviewing and recommending papers in their field. These specific communities are entitled Peer Community in X, e.g. Peer Community in Evolutionary Biology, Peer Community in Microbiology.


Running a 'dev' PCI
-------------------

Requirements:

	python (3.8+), postgreSql (9.6+), web2py (2.21+)
	libimage-exiftool-perl, ghostscript (9.26+)


Create a python virtual env:

	make virt-env


Install, configure, run:

	make install    # setup runtime requirements

	make db.admin   # give yourself postgres admin access
	make db         # create PostgreSql database and user

	make start      # run the PCI server


Browse the "empty" PCI at http://localhost:8000/

Note: this 'dev' PCI runs with no mail server configured, so no mail
will fly out; outbound and scheduled mails are however generally
available via menu Admin > Mailing queue.

On a 'prod' setup, mails are sent by the `mail_queue` cronjob.

See [Mailing-queue](doc/Mailing-queue.md) to run one.


Running tests
-------------

Automated tests run as selenium+pytest.

The tests can be used to populate an "empty" vanilla dev instance.

See [Tests setup](doc/Tests-setup.md) then use:

	make test.install # setup test requirements

	make test.reset
	make test.basic
	make test.full


Further reading
---------------

- [File structure](doc/File-structure.md)
- [COAR Notify](doc/COAR-Notify.md)
- [Docker](doc/Docker-container.md)
