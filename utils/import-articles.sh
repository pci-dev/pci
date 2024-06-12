#!/bin/bash

main() {
	users
	articles
	reco
	reviews
}

users() {
	FILE="t_users"
	TABLE="auth_user"
	import
}

articles() {
	FILE="t_articles"
	TABLE="t_articles"
	import
}

reco() {
	FILE="t_reco"
	TABLE="t_recommendations"
	import
}

reviews() {
	FILE="t_reviews"
	TABLE="t_reviews"
	import
}

import() {
	cat $FILE.txt | psql pci_test -c "copy $TABLE (`cat $FILE.exp.cols`) from STDIN"
}

main
