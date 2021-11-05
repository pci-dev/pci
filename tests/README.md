PCI automated testing
=====================

Python-based UI testing using:

- pytest as runner
- selenium as browser automation


Requirements
------------

	pip install -r requirements.txt

	sudo apt install chromium-chromedriver
	ln -s /usr/lib/chromium-browser/chromedriver ~/bin/


Running tests
-------------

all tests:

	pytest


specific tests:

	pytest -k login

	pytest test_about.py


Running non-headless
--------------------

comment out `option.headless = True` in `conftest.py`
