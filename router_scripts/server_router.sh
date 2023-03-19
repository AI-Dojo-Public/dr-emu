#!/bin/vbash
source /opt/vyatta/etc/functions/script-template
configure
set protocols static route 0.0.0.0/0 next-hop 192.168.50.10
commit
exit