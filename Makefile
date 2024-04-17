install: web2py pydeps postgresql additional

virt-env:
	sudo apt-get install virtualenvwrapper
	mkvirtualenv pci --python=`which python3.8`

web2py:
	git clone --depth=10 https://github.com/pci-dev/web2py
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

db.clean:
	$(psql) -c "drop database if exists main"
	$(psql) -c "drop role if exists pci_admin"

db.admin:
	echo "map_admin $$USER postgres" | sudo tee -a /etc/postgresql/*/main/pg_ident.conf
	sudo sed -i '/local *all *postgres *peer/ s/$$/ map=map_admin/' /etc/postgresql/*/main/pg_hba.conf
	sudo systemctl restart postgresql

psql = psql -q -U postgres -v "ON_ERROR_STOP=1"

start start.debug:
	web2py/web2py.py --password pci $(log) &

stop:
	@PID=`ps ax -o pid,args | grep web2py.py | grep -v grep | awk '{print $$1}'` ;\
	[ "$$PID" ] && kill $$PID && echo killed $$PID || echo "not running"

start: conf init

conf:	private/appconfig.ini

init:	logo

logo:	static/images/background.png \
	static/images/small-background.png

private/% static/%:
	cd $(dir $@) && cp sample.$(notdir $@) $(notdir $@)

start: log = > /dev/null


test.install.selenium: install.selenium install.firefox

install.selenium:
	pip install -r tests/requirements.txt

install.chromium:
	sudo apt install chromium-chromedriver

install.firefox:
	sudo apt install firefox-geckodriver

test.install: test.install.selenium

test.setup: test.db

test.db:
	$(psql) main < sql_dumps/insert_test_users.sql

test.db.rr:
	$(psql) main -c "delete from mail_templates"
	$(psql) main < sql_dumps/insert_default_mail_templates_pci_RR.sql

test.reset:	reset set.conf.rr.false
test.reset.rr:	reset set.conf.rr.true test.db.rr
reset:		stop db.clean db test.setup start

set.conf.rr.%:
	rm -f languages/default.py
	sed -i '/^registered_reports/ s/=.*/= $*/' private/appconfig.ini
	sed -i '/^scheduled_submissions/ s/=.*/= $*/' private/appconfig.ini

test.full test.basic test.medium test.scheduled-track: delete.external.user

test.full:		test_full.py
test.basic:		test_basic.py
test.medium:		test_medium.py
test.scheduled-track:	test_scheduled_track.py

test.full test.basic test.medium test.scheduled-track: test.clean


test.create-article:
	cd tests ; pytest -k "basic and User_submits"

test.review.registered-user:
	cd tests; pytest -v -k "review_article and Reviewer"

test.review.external:
	cd tests; pytest -v -k "review_article and External"

test.review.no-upload:
	cd tests; RR_SCHEDULED_TRACK=1 \
	pytest -v -k "review_article and Reviewer"

test_%:
	(cd tests; pytest -xv $@)

delete.external.user:
	$(psql) main -c "delete from auth_user where first_name='Titi';"

test.clean:
	pkill -9 -ef 'geckodriver[ ]|marionette[ ]' || true

coar.refresh:
	touch modules/app_modules/coar_notify.py

reload.web2py:
	touch ../../wsgihandler.py

recreate.v_article:
	~/all-pci-db.sh | while read db; do \
	psql -h mydb1 -p 33648 -U peercom $$db \
		< utils/re-create_v_article.sql; \
	done

setup.new-pci: dirs = errors/ uploads/ sessions/
setup.new-pci:
	mkdir -p $(dirs)
	chgrp www-data $(dirs) private
	chmod g+w $(dirs)
	chmod g+r private
	ln -s default_base.py languages/default.py

api:
	cat utils/api.sparse-checkout > .git/info/sparse-checkout
	cat utils/api.db_plug.py > models/db_plug.py
	git sparse-checkout init
	\rm -f languages/default.py
	cd controllers && ln -s api.py default.py

api.dismount:
	\rm -f controllers/default.py models/db_plug.py
	git sparse-checkout disable

check.static:
	@git diff --stat `git describe --tag --abbrev=0` \
	| grep static/ || echo "no update needed"

build:
	docker build -t pci .

dev:
	:
	: use ^C to quit
	:
	docker run --rm -it -p 8001:8001 -v `pwd`:/pci pci

log:
	@git log --merges --format=%s \
		`git describe --tag --abbrev=0`..
