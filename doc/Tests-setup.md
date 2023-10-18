PCI Automated Tests
===================

Requirements
------------

	make test.install
	make test.setup


Run tests
---------

full one-round scenario:

	make test.full

	show=y make test.full

shorter scenario:

	make test.basic
	make test.medium


Reset test environment
----------------------

	make test.reset
	make test.reset.rr  # for RR

	make test.clean     # kill dangling test-browsers
