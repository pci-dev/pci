# PCIDEV : Peer Community website dev

## A free recommendation process of published and unpublished scientific papers based on peer reviews

---

## What is PCI ?

The “Peer Community in” project is a non-profit scientific organization aimed at creating specific communities of researchers reviewing and recommending papers in their field. These specific communities are entitled Peer Community in X, e.g. Peer Community in Evolutionary Biology, Peer Community in Microbiology.

---

## Install project

Requirements: Python (3.6 or greater), PostgreSql (9.6 or greater), web2py.

Additional requirements: libimage-exiftool-perl

Suggestion: use a python virtual env

```bash
make py.venv
```

Install all required components:

```bash
make install
```

Create PostgreSql database and user
```bash
make db
```

Run the PCI server:

```bash
make start
```
creates default config files:
- `private/appconfig.ini`
- `private/reminders_config`

Run mailing queue:
On local host:
```bash
python web2py.py -S <app-name> -M -R applications/<app-name>/private/mail_queue.py
```

Via linux service : 
- Put the private/mailing-queue.service file in /etc/systemd/system/mailing-queue.service
- Change appname, and web2py path in ExecStart service command
- ```sudo servicectl start mailing-queue```

To get log in journalctl for mailing queue:
```bash
sudo apt-get install libsystemd-dev
pip install systemd 
```

**Don't forget to replace "<app-name>" in the command above.**

---

## Run tests

#### requirements :

- NodeJs >= 10
- npm >= 6 (come with nodejs)

Install all test components:

```bash
make test.install
```

#### create / configure test users :

```bash
make test.setup
```

#### Run tests :

```bash
make test
```

or live:
```bash
npx cypress open
```

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


# COAR Notify

PCI contains a demonstration [COAR Notify](https://notify.coar-repositories.org/) implementation, comprising a [Linked
Data Notifications inbox](https://www.w3.org/TR/ldn/#receiver) and the ability to send notifications to an external
pre-configured LDN inbox in response to endorsement events.

To configure COAR Notify, your `private/appconfig.ini` should contain the following section, with appropriate URLs:

```ini
[coar_notify]
inbox_url = http://remote-service.invalid/inbox
base_url = http://this-service.invalid/pci/
```

If `coar_notify.inbox_url` is missing or empty, COAR Notify support — both the inbox and outward notifications — is
disabled.