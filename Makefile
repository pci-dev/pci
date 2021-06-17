install: web2py pydeps postgresql


web2py:
	wget https://mdipierro.pythonanywhere.com/examples/static/web2py_src.zip
	unzip web2py_src.zip && rm web2py_src.zip
	ln -s ../.. web2py/applications/pci

pydeps:
	pip install -r requirements.txt

postgresql:
	sudo apt-get install -y postgresql postgresql-contrib

db:
	$(psql) -c "CREATE ROLE pci_admin WITH LOGIN PASSWORD 'admin4pci'"
	$(psql) -c "CREATE DATABASE main"
	$(psql) main -c "CREATE EXTENSION unaccent"
	$(psql) main < sql_dumps/pci_evolbiol_test.sql
	$(psql) main < sql_dumps/pci_evolbiol_test_data0.sql
	$(psql) main < sql_dumps/insert_default_help_texts.sql
	$(psql) main < sql_dumps/insert_default_mail_templates.sql
	$(psql) main < sql_dumps/t_status_article.sql
	$(psql) main -c "insert into help_texts_3 select * from help_texts"

db.clean:
	$(psql) -c "drop database if exists main"
	$(psql) -c "drop role if exists pci_admin"

psql = sudo -iu postgres psql

py.venv:
	type -t mkvirtualenv || sudo apt-get install virtualenvwrapper
	mkvirtualenv pci --python=`which python3`

start:
	web2py/web2py.py --password pci &

stop:
	PID=`ps aux | grep web2py.py | grep -v grep | awk '{print $$2}'` ;\
	[ "$$PID" ] && kill $$PID || echo "no running"

start: private/appconfig.ini
private/appconfig.ini:
	cp private/sample.appconfig.ini private/appconfig.ini

test.install:
	sudo apt-get install npm
	sudo npm install -g n
	sudo n stable
	sudo npm install -g npm@latest
	npm install

test.setup:
	$(psql) main < sql_dumps/insert_test_users.sql
	cp cypress/fixtures/_users.json cypress/fixtures/users.json


test:
	npx cypress run --spec cypress/integration/preprint_in_one_round.spec.js
