The PCI Mailing Queue
=====================

In prod setups, the mailing queues are run via a cronjob.
See `cron_tasks/crontab.prod`.


Setup a dev mailing queue
-------------------------

- configure the mail server in `appconfig.ini`
- run the mailing queue process


Run the mailing queue - 3 options:

1./ via cron:

- setup a cronjob (see `cron_tasks/`)


2./ directly:

	python web2py.py -S <app-name> -M -R applications/<app-name>/private/mail_queue.py


3./ via linux service:

- Put the private/mailing-queue.service file in /etc/systemd/system/mailing-queue.service
- Change appname, and web2py path in ExecStart service command
- ```sudo servicectl start mailing-queue```


**Don't forget to replace "`<app-name>`" in the command above.**



Logs in journalctl
------------------

The mailing queue can log to journald.


	sudo apt-get install libsystemd-dev
	pip install systemd
