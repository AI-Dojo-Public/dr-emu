FROM registry.gitlab.ics.muni.cz:443/244656/ai-dojo-docker-testbed:vyos-1.3 as wan_router

COPY ./router_configs/wan_router/config /opt/vyatta/etc/config

FROM registry.gitlab.ics.muni.cz:443/244656/ai-dojo-docker-testbed:vyos-1.3 as internal_router

COPY ./router_configs/user_router/config /opt/vyatta/etc/config
