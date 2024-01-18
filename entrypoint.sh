#!/bin/sh
echo $DOCKER_TOKEN | docker login $REGISTRY_URL --username $DOCKER_USERNAME --password-stdin
poetry run alembic upgrade head
exec "$@"
