FROM alpine:3.17 as base

RUN apk add --no-cache \
    bash

FROM base as node

FROM base as router

RUN apk add --no-cache \
    iptables

FROM ubuntu:latest as dr_emu
ARG POETRY_VIRTUALENVS_IN_PROJECT
ENV POETRY_VIRTUALENVS_IN_PROJECT $POETRY_VIRTUALENVS_IN_PROJECT

# Install system dependencies
RUN apt-get -y update
RUN apt-get -y install ca-certificates curl python3-dev g++ gcc
RUN install -m 0755 -d /etc/apt/keyrings
RUN curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
RUN chmod a+r /etc/apt/keyrings/docker.asc
RUN echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
RUN apt-get -y update
RUN apt-get -y install docker-ce-cli


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
