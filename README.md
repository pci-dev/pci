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


---

## Run tests

#### Requirements:

Selenium tests:

	make test.install.selenium

Cypress tests:

	make test.install

#### Setup test environment:

	make test.setup
	make test.setup test.db.rr  # for RR

#### Run tests:

	make test

or live:

	npx cypress open

shorter scenario:

	make test.basic

	SHOW=y make test.basic  # live-show

#### Reset test environment:

	make test.reset
	make test.reset.rr  # for RR

---

## Setup a dev docker container

### Build the dev container

	docker build -t pci .

### Run the dev container

A./ one-shot, throw-away

	docker run --rm -it -p 8001:8001 pci

use ^C to quit.


B./ long-running, keep state

	docker run -d -p 8001:8001 pci

use `docker stop` and `docker start` to stop/restart.
use `docker rm` to dispose.


C./ one-shot, throw away, with local dev env mapping

	docker run --rm -it -p 8001:8001 -v `pwd`:/pci pci

### Use the containerized PCI

	browse http://localhost:8001/pci

	docker exec -it <container id> sh

---

## Project Architecture :

### Important files and code structure :

```bash
private/
  appconfig.ini # Application configuration file (set)

controllers/
  [controller_name].py # Routes that return a web page
  [controller_name]_actions.py # Action to perform and then redirect

models/
  db.py # Define database structure and hooks
  menu.py # Define the navigation menu (and footer)

modules/
  app_components/ # Here, a component is a reusable function that render Html (most of components have a related html view file)
  app_modules/ # Common functions used by many controllers
  controller_modules/ # Functions used only in a specific controller
  imported_modules/ # Imported Modules

views/
  default/ # Common Html view, shared by multiple controller functions
  controller/ # Html views for specific controller functions
  component/ # Html views for components
  snippets/ # A snippet is just some reusable html, contrary to components no module function is needed to be run
  mail/ # Html mail layout

static/
  css/
    components/ # Css files for components / snippets
    *.css # Imported or common Css files
  js/ # Static js files
  images/ # Static images files
  fonts/ # Static fonts files

templates/
  # mail/ # Html templates for mails (most of content is text here)
  # text/ # Long text templates
  js/ # JavaScript templates (used to perform actions client-side)

cypress/
  integration/ # Define all tests
  supports/ # Define common commands for tests (such as login, check article status...)
  fixtures/ # Datas needed to run tests
```


COAR Notify
-----------

PCI contains a COAR Notify implementation.

See [doc / COAR Notify](doc/COAR-Notify.md).
