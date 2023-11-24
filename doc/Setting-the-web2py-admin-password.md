The web2py admin app & password
===============================

1./ Update or set the web2py admin password
-------------------------------------------

	cd ...   #  web2py root e.g. /var/www/web2py
	python3 -c 'from gluon.main import save_password; save_password("PASSWORD", 443)'


2./ Notes
---------
- web2py allows access to the admin app only over https
- the web2py admin app needs write access to ./private/
- re: deployment, see Fixing-the-web2py-admin-issue.md
