#!/bin/bash

PSQL="psql -U postgres main"
SOURCE_ID=5

NB_ITEMS=100

main() {
	create_tmp_tables

	for _ in `seq $NB_ITEMS`; do
		add_cloned_article
		printf "."
	done
	echo

	drop_tmp_tables
}


create_tmp_tables() {
$PSQL <<EOT
create table tmp_art as select * from t_articles where id = $SOURCE_ID;
create table tmp_reco as select * from t_recommendations where article_id = $SOURCE_ID;
EOT
}


add_cloned_article() {
$PSQL << EOT
update tmp_art set id = nextval('t_articles_id_seq');
update tmp_reco set id = nextval('t_recommendations_id_seq');

update tmp_reco set article_id = (select id from tmp_art);
update tmp_art set uploaded_picture = 't_articles.uploaded_picture.' || id || '.png';

insert into t_articles table tmp_art ;
insert into t_recommendations table tmp_reco ;
EOT
} >/dev/null


drop_tmp_tables() {
$PSQL <<EOT
drop table tmp_art;
drop table tmp_reco;
EOT
}


main "$@"
