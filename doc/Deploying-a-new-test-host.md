Deploying a new test host
=========================

To deploy a new test host:

- create a prod-like setup (web2py, apache, python)
- install a local postgres (with required extension)
- create local test databases (usualy 2, eb and rr)

Then:

- deploy test pci environments in web2py/applications/
- restore test-database dumps to test databases
- restore test uploads/ to new test environment
- check/configure test environments private/appconfig.ini
- setup crontabs (pci) for test sites
- setup auto-update (dev) crontab
