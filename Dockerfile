#ARG CONFIG

FROM registry.gitlab.ics.muni.cz:443/244656/ai-dojo-docker-testbed:vyos-1.3 as wan_router

COPY ./router_scripts/wan_router.sh /home/vyos/config.sh
RUN chmod +x /home/vyos/config.sh
#RUN ip route del default
#RUN ip route add default via 192.168.50.250
ENTRYPOINT ["/sbin/init", "&&", "/bin/bash", "-c", "./ksd.sh"]
#CMD ["&&", "runuser", "-u", "vyos", "-c", "/home/vyos/config.sh" ]