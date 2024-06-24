#!/bin/bash

DB=pci_test

main() {
	users
	articles
	reco
	reviews
	surveys
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

surveys() {
	FILE="t_surveys"
	TABLE="t_report_survey"
	import
}

import() {
	cat $FILE.txt | psql $DB -c "copy $TABLE (`cat $FILE.exp.cols`) from STDIN"
}

main
