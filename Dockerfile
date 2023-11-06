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
RUN apk add --no-cache build-base curl python3-dev g++ gcc


# install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# install python dependencies
RUN poetry config installer.max-workers 10
RUN poetry install --no-interaction --no-ansi -v

# run application
ENTRYPOINT ["poetry", "run", "uvicorn", "dr_emu.app:app", "--reload", "--host", "0.0.0.0"]

FROM base as cyst-demo
RUN apk update
RUN apk add --no-cache build-base curl python3-dev g++ gcc py3-pip git
RUN pip install cyst-core wheel