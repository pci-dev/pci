#!/bin/bash

DB=pci_ecology

FIELDS="first_name, last_name, email, country"


main() {
    case $1 in
        ""|-h|--help)
            echo "usage: $(basename $0) [reviewers|recommenders] [pci_xxx]"
            exit 0
            ;;
        reviewers|recommenders|users)
            cmd=$1
            DB=$2
            ;;
        *)
            echo "unknown command: $1"
            exit 1
            ;;
    esac

    get_$cmd
}

get_users() {

(db=$DB; psql -h mydb1 -p 33648 -U peercom $db ) << EOT

copy (

  select $FIELDS
  from auth_user
  order by id

) to stdout with CSV DELIMITER ';' HEADER;
EOT

}

get_reviewers() {

(db=$DB; psql -h mydb1 -p 33648 -U peercom $db ) << EOT

copy (

  select $FIELDS
  from auth_user
  where id in (
        select distinct reviewer_id from t_reviews where review_state = 'Review completed'
  ) order by id

) to stdout with CSV DELIMITER ';' HEADER;
EOT

}

get_recommenders() {

(db=$DB; psql -h mydb1 -p 33648 -U peercom $db ) << EOT

copy (

  select $FIELDS
  from auth_user
  where id in (
        select user_id from auth_membership where group_id = 2
  ) order by id

) to stdout with CSV DELIMITER ';' HEADER;
EOT
}

main "$@"
