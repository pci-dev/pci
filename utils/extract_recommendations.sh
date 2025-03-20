#!/bin/bash

HOST=$1

TARGET="$HOST/admin/extract_recommendations"
PARAMS="start_year=$2&end_year=${3:-$2}"

[ "$1" ] || {
	echo "usage: $0 <pci host> <start year> [end year] (default: start year)"
	exit 1
}

CREDENTIALS=~/.pci-login
[ -f $CREDENTIALS ] || {
	cat <<EOT
:
: creating $CREDENTIALS
: please provide credentials in there.
:
EOT
	cat > $CREDENTIALS <<EOT
LOGIN=
PASSW=
EOT
}
source $CREDENTIALS

[ "$LOGIN" ] && [ "$PASSW" ] || {
	echo login/password not defined
	exit 1
}
LOGIN_URL="$HOST/default/user/login"


CURL="curl -s -b .cookies -c .cookies"

formkey=$(
$CURL \
	$LOGIN_URL \
	| sed 's/<input /\n/g' \
	| grep formkey | sed 's/.*value="\(.*\)".*/\1/'
)
$CURL \
	--data "email=$LOGIN&password=$PASSW&_next=/&_formname=login&_formkey=$formkey" \
	$LOGIN_URL \
	> /dev/null

$CURL \
	"$TARGET?$PARAMS"
