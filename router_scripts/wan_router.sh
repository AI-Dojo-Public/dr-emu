#!/bin/vbash
source /opt/vyatta/etc/functions/script-template
ip route del default
ip route add default via 192.168.50.250
su - vyos
configure
set protocols static route 0.0.0.0/0 next-hop 192.168.50.250
set protocols static route 192.168.91.0/24 next-hop 192.168.50.11
set protocols static route 192.168.92.0/24 next-hop 192.168.50.12
set nat source rule 100 outbound-interface 'eth0'
set nat source rule 100 source address '192.168.0.0/16'
set nat source rule 100 translation address masquerade
commit
exit