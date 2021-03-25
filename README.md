# PCIDEV : Peer Community website dev

## A free recommendation process of published and unpublished scientific papers based on peer reviews

---

## What is PCI ?

The “Peer Community in” project is a non-profit scientific organization aimed at creating specific communities of researchers reviewing and recommending papers in their field. These specific communities are entitled Peer Community in X, e.g. Peer Community in Evolutionary Biology, Peer Community in Microbiology.

---

## Install project

Intsall Python 3.6 or greater
Intsall PostgreSql 9.6 or greater

Install python dependencies :

```bash
pip install requierment.txt
```

Create PostgreSql database

Import help texts :

```bash

```

Create admin user :

```bash

```

Create or fill the configuration file with your credentials :

```ini
# private/appconfig.ini
[db]
uri = postgres:psycopg2://<db_user>:<db_password>@<db_host>:<db_port>/<db_name>

[smtp]
server =
sender =
login =
tls =
ssl =

[captcha]
public =
private =

[social]
tweeter =
tweethash =
tweeter_id =
tweeter_consumer_key =
tweeter_consumer_secret =
tweeter_access_token =
tweeter_access_token_secret =
```

Run project :

```bash
python web2py.py
```

Run mailing queue :
In local : 
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

Install nodejs dependencies :

```bash
npm install
```

#### create / configure test users :

Create cypress/fixtures/user.json file and fill it with the users credentials for each roles as follow :

```json
{
  "admin": {
    "firstname": "[FILL WITH USER FIRSTNAME]",
    "lastname": "[FILL WITH USER lASTNAME]",
    "mail": "[FILL WITH USER MAIL]",
    "password": "[FILL WITH USER PASSWORD]"
  },
  "developer": {
    "firstname": "[FILL WITH USER FIRSTNAME]",
    "lastname": "[FILL WITH USER lASTNAME]",
    "mail": "[FILL WITH USER MAIL]",
    "password": "[FILL WITH USER PASSWORD]"
  },
  "manager": {
    "firstname": "[FILL WITH USER FIRSTNAME]",
    "lastname": "[FILL WITH USER lASTNAME]",
    "mail": "[FILL WITH USER MAIL]",
    "password": "[FILL WITH USER PASSWORD]"
  },
  "recommender": {
    "firstname": "[FILL WITH USER FIRSTNAME]",
    "lastname": "[FILL WITH USER lASTNAME]",
    "mail": "[FILL WITH USER MAIL]",
    "password": "[FILL WITH USER PASSWORD]"
  },
  "co_recommender": {
    "firstname": "[FILL WITH USER FIRSTNAME]",
    "lastname": "[FILL WITH USER lASTNAME]",
    "mail": "[FILL WITH USER MAIL]",
    "password": "[FILL WITH USER PASSWORD]"
  },
  "normal_user": {
    "firstname": "[FILL WITH USER FIRSTNAME]",
    "lastname": "[FILL WITH USER lASTNAME]",
    "mail": "[FILL WITH USER MAIL]",
    "password": "[FILL WITH USER PASSWORD]"
  }
}
```

#### Run tests :

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
