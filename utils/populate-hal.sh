pci=$1
article_id=$2
hal_url=$3
rec_doi=${4:-$article_id}


usage() { echo "usage: $0 <pci> <article id> <hal url> [rec doi]"; exit 1; }

[ "$1" ] && [ "$2" ] && [ "$3" ] || usage


curl --fail -s \
	-H "Content-Type: application/ld+json" \
	-A "peercommunityin.org" \
	-d @- \
	https://inbox.hal.science/ \
	> /dev/null \
<<EOT
{
    "@context": [
        "https://www.w3.org/ns/activitystreams",
        "https://purl.org/coar/notify"
    ],
    "id": "urn:$(uuidgen)",
    "origin": {
        "id": "https://$pci.peercommunityin.org/coar_notify/",
        "inbox": "https://$pci.peercommunityin.org/coar_notify/inbox/",
        "type": [
            "Service"
        ]
    },
    "target": {
        "id": "https://inbox.hal.science/",
        "inbox": "https://inbox.hal.science/",
        "type": [
            "Service"
        ]
    },
    "type": [
        "Announce",
        "coar-notify:EndorsementAction"
    ],
    "context": {
        "id": "$hal_url",
        "ietf:cite-as": "$hal_url",
        "type": "sorg:AboutPage"
    },
    "object": {
        "id": "https://$pci.peercommunityin.org/articles/rec?articleId=$article_id",
        "type": [
            "Page",
            "sorg:WebPage"
        ],
	"ietf:cite-as": "https://doi.org/10.24072/pci.$pci.1$(printf '%05d' $rec_doi)"
    },
    "actor": {
        "id": "https://peercommunityin.org/dev",
        "type": [
            "Person"
        ],
        "name": "DEV Injector"
    }
}
EOT
