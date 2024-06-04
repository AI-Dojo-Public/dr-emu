FROM mysql:8-debian as production

COPY docker/initial.sql /docker-entrypoint-initdb.d/initial.sql
COPY docker/1-database.sql /docker-entrypoint-initdb.d/1-database.sql
