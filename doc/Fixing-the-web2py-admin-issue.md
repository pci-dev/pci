Fixing the web2py admin issue
=============================

web2py comes with a default admin app that is:

- conflicting with PCI's /admin menu URLs
  (on a wsgi setup as per pci prod)

- a must-have to access internal-error tickets


1./ rename the web2py admin app
-------------------------------

	cd /var/www/web2py/applications
	mv admin web2py


2./ create web2py flavour admin passwd
--------------------------------------

	cd ../.. # i.e. web2py root e.g. /var/www/web2py
	python3 -c 'from gluon.main import save_password; save_password("PASSWORD", 443)'


3./ route tickets to new url
----------------------------

in the toplevel `/routes.py`, add:

```
# direct tickets to /web2py instead of /admin
error_message_ticket = '''<html><body><h1>Internal error</h1>
     Ticket issued: <a href="/web2py/default/ticket/%(ticket)s"
     target="_blank">%(ticket)s</a></body></html>'''
```


Note: the dev/test setup uses a diffrent routing scheme does not have the conflict issue
