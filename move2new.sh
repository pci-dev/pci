#!/bin/bash -x

dir_name="/var/www/peercommunityin/"

## TRY LINK ON CURRENT VERSION
# cd $dir_name
# mv web2py web2py214
# ln -s web2py214 web2py
## OK! :-)

## NO!!!!: COPY SESSIONS TO NEW DIR
## CLEAR ALL SESSIONS
pci="PCICNeuro"   ;  cd $dir_name/web2py217/applications/$pci ; rm -rf sessions ; mkdir sessions ; chgrp www-data sessions ; chmod g+w sessions
pci="PCICompStat" ;  cd $dir_name/web2py217/applications/$pci ; rm -rf sessions ; mkdir sessions ; chgrp www-data sessions ; chmod g+w sessions
pci="PCIPaleo"    ;  cd $dir_name/web2py217/applications/$pci ; rm -rf sessions ; mkdir sessions ; chgrp www-data sessions ; chmod g+w sessions
pci="PCIEcology"  ;  cd $dir_name/web2py217/applications/$pci ; rm -rf sessions ; mkdir sessions ; chgrp www-data sessions ; chmod g+w sessions
pci="PCIEvolBiol" ;  cd $dir_name/web2py217/applications/$pci ; rm -rf sessions ; mkdir sessions ; chgrp www-data sessions ; chmod g+w sessions


## LINK ON NEW VERSION
cd $dir_name
rm web2py ; ln -s web2py217 web2py

## REVERT...
# # cd $dir_name
# # rm web2py ; ln -s web2py214 web2py


