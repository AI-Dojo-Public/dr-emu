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

# Install system dependencies
RUN apk add --no-cache build-base curl python3-dev g++ gcc

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Install application and dependencies
COPY . .
RUN poetry install --no-interaction --no-ansi
RUN poetry run pip install --upgrade setuptools  # In order for CYST to work on Python >= 3.12

# Link dr-emu executable
RUN ln -s /app/.venv/bin/dr-emu /root/.local/bin/dr-emu

# Run application
ENTRYPOINT [ "/app/entrypoint.sh" ]
CMD ["poetry", "run", "uvicorn", "dr_emu.app:app", "--reload", "--host", "0.0.0.0"]

