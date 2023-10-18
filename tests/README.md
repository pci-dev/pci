PCI automated testing
=====================

Python-based UI testing using:

- pytest as runner
- selenium as browser automation


Requirements
------------

	pip install -r requirements.txt
	sudo apt install chromium-chromedriver


Running tests
-------------

all tests:

	pytest


specific tests:

	pytest test_about.py

	pytest -k "login and not setup_article"


Running non-headless
--------------------

	show=y pytest -k about
