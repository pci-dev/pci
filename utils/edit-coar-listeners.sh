main() {
case $1 in
    ""|-h|--help)
        echo "usage: $0 edit | inspect"
        ;;
    edit)
        read -p "did you inspect the edit script ? [ctrl-C if not]"
        echo "applying conf edits"
        edit_conf
        ;;
    inspect)
        echo "---------------------------------------"
        echo "The following script will run on 'edit'"
        echo "---------------------------------------"
        echo
        sed '1, /^edit_conf()/ d; /^# edit_conf/, $ d' $0
        ;;
    *)
        echo "unknown command: $1"
        $0
        exit 1
        ;;
esac
}

edit_conf() {
sed -i '
/listeners =/ s/=.*/= sciety,sciety-test,/

/sciety_inbox =/ s|=.*|= https://inbox-sciety-prod.elifesciences.org/inbox/|

/sciety_inbox/ a\
\
sciety-test_id = https://sciety.org/\
sciety-test_inbox = https://coar-notify-inbox.fly.dev/inbox\
\
' sites/PCI*/private/appconfig.ini

# edit_conf
}

main "$@"
