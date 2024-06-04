#!/bin/sh

echo "mysqldump -u ${DATABASE_USER} -h ${DATABASE_HOST} --password=${DATABASE_PASSWORD} --no-tablespaces ${DATABASE_NAME}" >> .bash_history

sudo service ssh start

printenv | grep CRYTON_WORKER_ > /tmp/env
sudo mv /tmp/env $HOME/.local/cryton-worker/.env
sudo chown $USER_NAME:$USER_NAME $HOME/.local/cryton-worker/.env
sudo su $USER_NAME -c $HOME/entrypoint.sh

exec "$@"
