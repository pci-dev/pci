#!/bin/bash

set -x

BASE="https://evolbiol.peercommunityin.org"

CREDENTIALS=~/.pci-login
[ -f $CREDENTIALS ] || {
	:
	: creating $CREDENTIALS, please provide credentials in there.
	:
	cat > $CREDENTIALS <<EOT
LOGIN=
PASSW=
EOT
}
source $CREDENTIALS

[ "$LOGIN" ] && [ "$PASSW" ] || {
	: login/password not defined
	exit 1
}

appname=$(
wget -q -O - $BASE \
	| grep application-name | sed 's/.*content="//;s/".*//'
)
LOGIN_URL="$BASE/default/user/login"
DATA_URL="$BASE/$appname/admin/mailing_lists"

COOKIES=cookies.txt

WGET="wget -q -O -
	--keep-session-cookies
	--save-cookies=$COOKIES
	--load-cookies=$COOKIES
"

formkey=$(
$WGET \
	$LOGIN_URL \
	| sed 's/<input /\n/g' \
	| grep formkey | sed 's/.*value="\(.*\)".*/\1/' 
)

$WGET \
	--post-data "email=$LOGIN&password=$PASSW&_next=/&_formname=login&_formkey=$formkey" \
	$LOGIN_URL \
	> main.html

$WGET \
	$DATA_URL \
	> data.html

cat data.html \
	| grep Roles | sed 's/<[^>]*>/\n/g' | sed 's/, /\n/g' \
	> data.txt
