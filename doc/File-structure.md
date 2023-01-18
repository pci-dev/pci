Project File Structure
======================

PCI is a `web2py` application, with a standard web2py file structure.


Important files and code structure
----------------------------------

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
  uploads/ # symlink to ../uploads = uploaded images, exposed publicly

templates/
  js/ # JavaScript templates (used to perform actions client-side)

cypress/
  integration/ # Define all tests
  supports/ # Define common commands for tests (such as login, check article status...)
  fixtures/ # Datas needed to run tests
```
