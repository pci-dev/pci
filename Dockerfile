FROM alpine:latest

RUN	apk add \
		python3 \
		postgresql \
		postgresql-contrib \
		exiftool \
		ghostscript \
	;
RUN	wget https://mdipierro.pythonanywhere.com/examples/static/web2py_src.zip \
	&& unzip web2py_src.zip \
	&& rm web2py_src.zip
RUN	ln -s ../../pci web2py/applications

RUN	mkdir pci
WORKDIR pci

COPY	requirements.txt .
RUN	sed -i s/psycopg2-binary/psycopg2/ requirements.txt
RUN	apk add py3-lxml py3-psycopg2 py3-pillow py3-pip
RUN	pip3 install -r requirements.txt

RUN	apk add sudo make
COPY	Makefile .

ENV PGDATA /var/lib/postgresql/data

RUN	for dir in $PGDATA /run/postgresql ; do \
		mkdir $dir ; chown postgres:postgres $dir ;\
	done

USER postgres

RUN	initdb &&\
	echo "host all  all    0.0.0.0/0  md5" >> $PGDATA/pg_hba.conf &&\
	echo "listen_addresses='*'" >> $PGDATA/postgresql.conf

USER root

COPY	sql_dumps sql_dumps

RUN	sudo -Eu postgres pg_ctl start -w	;\
	make db test.db				;\
	sudo -Eu postgres pg_ctl stop

RUN	ln -s python3 /usr/bin/python
COPY	docker/entrypoint.sh /

RUN	apk add nginx \
	; mkdir -p /run/nginx
COPY	docker/nginx.conf /etc/nginx/conf.d/default.conf

COPY	. .
RUN	make conf init

ENV PCI_PASSWORD pci

CMD	[ "/entrypoint.sh" ]

EXPOSE 8001
