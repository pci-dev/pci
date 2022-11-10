Fixing the web2py admin issue
=============================

web2py comes with a default admin app that is:

- conflicting with PCI's /admin menu URLs
- needs patching for python3 (as of web2py 2.21)


0./ rename the web2py admin app
-------------------------------

	cd /var/www/web2py/applications
	mv admin web2py


1./ patch it
------------

controllers/appadmin.py
models/access.py

see diffs below.

source: https://github.com/web2py/web2py/issues/2173


2./ create web2py flavour admin passwd
--------------------------------------

	cd ../.. # i.e. web2py root e.g. /var/www/web2py
	python3 -c 'from gluon.main import save_password; save_password("PASSWORD", 443)'


4./ add apache protection (optional)
------------------------------------

.htaccess
.htpasswd

	vi .htaccess
	htpasswd -cm .htpasswd pci

	chmod o-r .ht*
	chgrp www-data .ht*


annex: the patch
----------------

```
/var/www/peercommunityin/web2py/applications/web2py

diff -u controllers/appadmin.py{.orig,}
diff -u models/access.py{.orig,}


--- controllers/appadmin.py.orig	2020-11-28 05:10:46.000000000 +0100
+++ controllers/appadmin.py	2022-11-10 08:35:24.751299710 +0100
@@ -35,7 +35,8 @@
     request.is_local = True
 elif (remote_addr not in hosts) and (remote_addr != '127.0.0.1') and \
     (request.function != 'manage'):
-    raise HTTP(200, T('appadmin is disabled because insecure channel'))
+    #raise HTTP(200, T('appadmin is disabled because insecure channel'))
+    raise HTTP(200, 'appadmin is disabled because insecure channel')
 
 if request.function == 'manage':
     if not 'auth' in globals() or not request.args:



--- models/access.py.orig	2020-11-28 05:09:35.000000000 +0100
+++ models/access.py	2022-11-10 08:46:21.930600599 +0100
@@ -29,7 +29,8 @@
      request.client.startswith(request.env.trusted_lan_prefix):
     request.is_local = True
 elif not request.is_local and not DEMO_MODE:
-    raise HTTP(200, T('Admin is disabled because insecure channel'))
+    #raise HTTP(200, T('Admin is disabled because insecure channel'))
+    raise HTTP(200, 'Admin is disabled because insecure channel')
 
 try:
     _config = {}
@@ -38,7 +39,7 @@
         read_file(apath('../parameters_%i.py' % port, request)), _config)
 
     if not 'password' in _config or not _config['password']:
-        raise HTTP(200, T('admin disabled because no admin password'))
+        raise HTTP(200, 'admin disabled because no admin password')
 except IOError:
     import gluon.fileutils
     if is_gae:
@@ -47,10 +48,10 @@
             session.last_time = time.time()
         else:
             raise HTTP(200,
-                       T('admin disabled because not supported on google app engine'))
+                       'admin disabled because not supported on google app engine')
     else:
         raise HTTP(
-            200, T('admin disabled because unable to access password file'))
+            200, 'admin disabled because unable to access password file')
 
 
 def verify_password(password):
```
