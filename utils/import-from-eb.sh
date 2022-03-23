#!/bin/bash


main() {
	source_db=pci_evolbiol
	target_db=$(get_local_db)

	dump_import "help_texts"
	dump_import "mail_templates"
	fixup_id_seq "mail_templates"
	#dump_import "t_status_article" "CASCADE"
}

dump_import() {
	table=$1
	truncate_opt=$2

	psql $PSQL_AUTH $target_db -c "TRUNCATE $table $truncate_opt;"
	pg_dump $PSQL_AUTH $source_db -F p -O \
		-t $table \
		-a --inserts --column-inserts \
	| psql $PSQL_AUTH $target_db

	# or: pg_dump $PSQL_AUTH --table=$table --data-only $source_db
}

fixup_id_seq() {
	table=$1

	psql $PSQL_AUTH $target_db -c "
	SELECT pg_catalog.setval(
		'${table}_id_seq',
		(SELECT max(id)+1 FROM $table),
		true
	);
	"
}

get_local_db() {
	cat private/appconfig.ini | db_from_config
}

db_from_config() {
	grep psyco | sed s:.*/::
}

PSQL_AUTH="-h mydb1 -p 33648 -U peercom"

main
