FROM alpine:3.17 as base

RUN apk add --no-cache \
    bash

FROM base as node

FROM base as router

RUN apk add --no-cache \
    iptables

FROM docker:latest as aidojo-app
ENV POETRY_VIRTUALENVS_IN_PROJECT=true

# Copy app
COPY . /app/

# install system dependencies
RUN apk add --no-cache build-base curl python3

# install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# install python dependencies
RUN poetry install --no-interaction --no-ansi -vvv

# run application
ENTRYPOINT ["poetry", "run", "uvicorn", "testbed_app.app:app", "--reload", "--host", "0.0.0.0"]