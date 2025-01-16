#!/bin/bash

CMD=${1}
DB=${2:-pci_ecology}

YEAR=${year:-$(date +%Y)}
YEAR1=$((YEAR - 1))

ANON=${anon:-not null} # all reviews (anon or not)

FIELDS="first_name, last_name, email, country, registration_datetime"

PSQL="psql -h mydb1 -p 33648 -U peercom $DB"

main() {
    case $1 in
        ""|-h|--help)
            echo "usage: $(basename $0) [reviewers|recommenders|authors|users] [pci_xxx]"
            exit 0
            ;;
          users                           \
        | reviewers    | reviewers2       \
        | recommenders | recommenders2    \
        | authors      | authors2         \
        | new_recommenders                \
        )
            ;;
        *)
            echo "unknown command: $1"
            exit 1
            ;;
    esac

    get_$CMD | csv | $PSQL
}

csv() {
    echo "copy ("
    cat
    echo ") to stdout with CSV DELIMITER ';'"
    # or CSV DELIMITER ';' HEADER
}


get_users() {
cat << EOT

  select $FIELDS
  from auth_user
  order by id

EOT
}

get_reviewers2() {
cat << EOT

  select $FIELDS
  from auth_user
  where id in (
        select distinct reviewer_id from t_reviews where review_state = 'Review completed'
  ) order by id

EOT
}

get_reviewers() {

cat << EOT

  select $FIELDS
  from auth_user
  where id in (
        select distinct reviewer_id from t_reviews
        where
                review_state = 'Review completed'
                and
		acceptation_timestamp > '$YEAR1-01-01'
                and
                acceptation_timestamp < '$YEAR-01-01'
                and
                anonymously is $ANON
  ) order by id

EOT
}

get_recommenders2() {
cat << EOT

  select $FIELDS
  from auth_user
  where id in (
        select user_id from auth_membership where group_id = 2
  ) order by id

EOT
}

get_new_recommenders() {
cat << EOT

  select $FIELDS
  from auth_user
  where id in (
	select user_id from auth_membership where group_id = 2
	and registration_datetime >= '2022-01-01'
  ) order by id

EOT
}

get_recommenders() {
cat << EOT

  select $FIELDS
  from auth_user
  where id in (
        select distinct recommender_id from t_recommendations
        where
                recommendation_state = 'Recommended'
                and validation_timestamp >= '$YEAR1-01-01'
                and validation_timestamp <  '$YEAR-01-01'
  )

EOT
}

get_authors2() {
cat << EOT

  select $FIELDS
  from auth_user
  where id in (
        select distinct user_id from t_articles
  ) order by id

EOT
}

get_authors() {
cat << EOT

  select $FIELDS
  from auth_user
  where id in (
        select distinct user_id from t_articles
        where id in (
        select distinct article_id from t_recommendations
        where
                recommendation_state = 'Recommended'
                and validation_timestamp >= '$YEAR1-01-01'
                and validation_timestamp <  '$YEAR-01-01'
        )
  ) order by id

EOT
}


main "$@"
