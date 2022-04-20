#!/bin/bash

sites=(
evolbiol
ecology
microbiol
paleo
animsci
zool
neuro
genomics
mcb
forestwoodsci
archaeo
networksci
rr
ecotoxenvchem
infections
compstat
)

get_site_version() {
	site=$1

	version=$(curl -s https://${site}.peercommunityin.org/about/version \
		| grep HEAD \
		| sed 's:).*:):' \
		| sed 's:&gt;:>:'
	)
	printf "%-20s: %s\n" "$site" "$version"
}

main() {
	tmp=$(mktemp)

	rm -f $tmp

	for site in ${sites[*]}; do
		get_site_version $site >> $tmp &
	done
	wait
	sort $tmp
	rm $tmp
}

main
