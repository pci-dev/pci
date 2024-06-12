#!/bin/bash

DB="pci_evolbiol"
ARTICLES="709, 716, 664, 705, 657"

PSQL() { psql -h mydb1 -p 33648 -U peercom $DB; }

main() {
	articles
	reco
	reviews
	users

	wc -l t_*.txt
}

articles() {
	FILE=t_articles
	TABLE=t_articles
	USER_ID=user_id
	LINK_ARTICLES="id in ($ARTICLES)"

	export_table
}

reco() {
	FILE=t_reco
	TABLE=t_recommendations
	USER_ID=recommender_id
	LINK_ARTICLES="article_id in ($ARTICLES)"

	export_table
}

reviews() {
	FILE=t_reviews
	TABLE=t_reviews
	USER_ID=reviewer_id
	LINK_ARTICLES="recommendation_id in (
		select id from t_recommendations where article_id in ($ARTICLES))"

	export_table
}

users() {
	FILE=t_users
	TABLE=auth_user

	cat *.users.txt | sort -u > $FILE.txt
	export_cols
}


export_table() {
	LINK_USERS="id in (select $USER_ID from $TABLE where $LINK_ARTICLES)"

	PSQL <<< "copy (select * from $TABLE where $LINK_ARTICLES) to STDOUT ;" > $FILE.txt
	PSQL <<< "copy (select * from auth_user where $LINK_USERS) to STDOUT ;" > $FILE.users.txt
	export_cols
}

export_cols() {
	PSQL <<< "copy (select * from $TABLE where id = 0) to STDOUT with (format csv, header );" > $FILE.exp.cols
}

main
