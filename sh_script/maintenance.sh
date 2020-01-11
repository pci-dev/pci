#!/bin/bash -x

src_name="/home/piry/W/web2py_2.17.2/applications/pcidev/"

dir_name="/var/www/peercommunityin/web2py/applications/"

scp $src_name/views/default/index.html peercom@peercom-front1:$dir_name/PCICompStat/views/default
scp $src_name/views/default/index.html peercom@peercom-front1:$dir_name/PCICNeuro/views/default
scp $src_name/views/default/index.html peercom@peercom-front1:$dir_name/PCIPaleo/views/default
scp $src_name/views/default/index.html peercom@peercom-front1:$dir_name/PCIEvolBiol/views/default
scp $src_name/views/default/index.html peercom@peercom-front1:$dir_name/PCIEcology/views/default

