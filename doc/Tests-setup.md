PCI Automated Tests
===================

Requirements
------------

	make test.install


Setup test environment
----------------------

	make test.setup
	make test.setup test.db.rr  # for RR


Run tests
---------

full one-round scenario:

	make test.full

	SHOW=y make test.full

shorter scenario:

	make test.basic

	SHOW=y make test.basic  # live-show


Reset test environment
----------------------

	make test.reset
	make test.reset.rr  # for RR
