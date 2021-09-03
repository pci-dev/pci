install: web2py pydeps postgresql additional


web2py:
	wget https://mdipierro.pythonanywhere.com/examples/static/web2py_src.zip
	unzip web2py_src.zip && rm web2py_src.zip
	ln -s ../.. web2py/applications/pci

pydeps:
	pip install -r requirements.txt

postgresql:
	sudo apt-get install -y postgresql postgresql-contrib

additional:
	sudo apt-get install -y libimage-exiftool-perl

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
	@PID=`ps ax -o pid,args | grep web2py.py | grep -v grep | awk '{print $$1}'` ;\
	[ "$$PID" ] && kill $$PID && echo killed $$PID || echo "no running"

start: private/appconfig.ini private/reminders_config

init:	static/images/background.png \
	static/images/small-background.png \
	static/images/RSS_datamatrix.png

private/%:
	cp private/sample.$* $@

static/images/%:
	cp static/images/sample.$* $@

test.install:
	sudo apt-get install npm
	sudo npm install -g n
	sudo n stable
	sudo npm install -g npm@latest
	npm install

test.setup: test.db cypress/fixtures/users.json

test.db:
	$(psql) main < sql_dumps/insert_test_users.sql

cypress/fixtures/%:
	cp $(dir $@)_$(notdir $@) $@

test.reset: stop db.clean db test.setup start

test:
	npx cypress run --spec cypress/integration/preprint_in_one_round.spec.js
test.basic:
	npx cypress run --spec cypress/integration/setup_article_for_review.js
