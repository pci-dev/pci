#!/bin/bash

set -x

SITES="
archaeo
animsci
ecology
compstat
evolbiol
microbiol
ecotoxenvchem
forestwoodsci
networksci
infections
genomics
neuro
paleo
zool
mcb
rr
"

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

set +x

[ "$LOGIN" ] && [ "$PASSW" ] || {
	echo login/password not defined
	exit 1
}

get_data() {

appname=$(
wget -q -O - $BASE \
	| grep application-name | sed 's/.*content="//;s/".*//'
)
LOGIN_URL="$BASE/default/user/login"
DATA_URL="$BASE/$appname/admin/mailing_lists"

TEMP=$(mktemp)
COOKIES=$TEMP.cookies

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
	> $TEMP.main.html

$WGET \
	$DATA_URL \
	> $TEMP.data.html

cat $TEMP.data.html \
	| grep Roles | sed 's/<[^>]*>/\n/g' | sed 's/, /\n/g' \
	;

rm -f $TEMP*
}


split_to_files() {
	for role in recommender manager administrator developer \
			Authors: Reviewers: Others: ;
	do
		sed "1,/^$role$/ d; /^[a-zA-Z:]*$/,$ d" \
			$site.txt > $site.$role.txt
	done
}


for site in $SITES; do
	BASE="https://$site.peercommunityin.org"
	(
	get_data > $site.txt
	split_to_files
	rm -f $site.txt
	) &
done
wait

for role in recommender Reviewers: Authors: Others: ; do
	target=$(echo $role | sed 's/s:$//' | tr '[A-Z]' '[a-z]')
	cat *.$role.txt | sort -u > $target.txt
done
