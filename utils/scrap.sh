#!/bin/bash


SITES="
archaeo
animsci
ecology
evolbiol
microbiol
ecotoxenvchem
forestwoodsci
healthmovsci
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


declare -A header=(
[administrator]="administrator"
[recommender]="recommender"
[developer]="developer"
[manager]="manager"
[author]="Authors:"
[other]="Other users (no role, not listed above):"
[reviewer.A]="Users with completed or awaiting reviews:"
[reviewer.B]="Users with completed reviews for recommended or rejected preprints:"
[newsletter]="Users receiving the newsletter:"
)

split_to_files() {
	for role in recommender manager administrator developer \
			author reviewer.{A,B} other newsletter;
	do
		sed "1,/^${header[$role]}$/ d; /^[a-zA-Z: ]*$/,$ d" \
			$site.txt > $site.$role.txt
	done
}


echo "$SITES"

for site in $SITES; do
	BASE="https://$site.peercommunityin.org"
	(
	get_data > $site.txt
	split_to_files
	printf "."
	) &
done
wait
echo

mkdir -p site

for target in manager recommender reviewer.{A,B} author other newsletter ; do
	cat *.$target.txt | sort -u > $target.txt
	for site_file in *.$role.txt; do
		site=${site_file%%.*}
		cat $site_file | sort -u > site/$site.$target.txt
	done
done

for site in $SITES; do
	rm -f $site.*
done

wc -l *.txt | grep -v total
