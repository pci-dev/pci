while true; do
    printf "`date +%T` "
    free | awk '/Mem:/ {print "mem used: " int($3/$2*1000)/10 "%"}'
    sleep 10
done
