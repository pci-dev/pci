#!/bin/bash

on_prod() {
	HOST=pci-prod:/var/www/peercommunityin/web2py/applications/
	SITE=PCIRegisteredReports
}

on_test() {
	HOST=pci-test:sites/
	SITE=PCiEvolBiol3
}

on_prod
rsync -av $HOST/$SITE/errors .
