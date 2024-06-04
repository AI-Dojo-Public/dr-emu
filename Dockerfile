FROM alpine:3.17 as base

RUN apk add --no-cache \
    bash

FROM base as node

FROM base as router

RUN apk add --no-cache \
    iptables

FROM docker:latest as dr_emu
ARG POETRY_VIRTUALENVS_IN_PROJECT
ENV POETRY_VIRTUALENVS_IN_PROJECT $POETRY_VIRTUALENVS_IN_PROJECT

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
RUN poetry run pip install --upgrade setuptools  # In order for CYST to work on Python3.12
RUN ln -s /app/.venv/bin/dr-emu /root/.local/bin/dr-emu

# run application
ENTRYPOINT [ "/app/entrypoint.sh" ]
CMD ["poetry", "run", "uvicorn", "dr_emu.app:app", "--reload", "--host", "0.0.0.0"]

