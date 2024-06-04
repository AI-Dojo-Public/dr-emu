FROM wordpress:6.3.0-php8.2-apache as production

ENV WP_HOSTNAME=wordpress_node
ENV WP_ADMIN_NAME=wordpress
ENV WP_ADMIN_PASSWORD=wordpress

RUN curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && \
    chmod +x wp-cli.phar && \
    mv wp-cli.phar /usr/local/bin/wp

COPY --chown=www-data:www-data --chmod=700 docker/entrypoint.sh /tmp/entrypoint.sh
COPY docker/index.php /usr/src/wordpress/index.php
