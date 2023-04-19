FROM alpine:3.17 as base

RUN apk add --no-cache \
    bash

FROM base as node

FROM base as router

RUN apk add --no-cache \
    iptables
