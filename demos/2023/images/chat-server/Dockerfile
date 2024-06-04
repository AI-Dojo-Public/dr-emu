FROM php:8-apache-bookworm as production

RUN docker-php-ext-install pdo pdo_mysql

COPY docker/app/ /var/www/html/


