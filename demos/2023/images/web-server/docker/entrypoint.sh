#!/bin/sh

su www-data --shell=/bin/bash -c "wp core install --path=/usr/src/wordpress/ --url=http://$WP_HOSTNAME --title=CDRI --admin_name=$WP_ADMIN_NAME --admin_password=$WP_ADMIN_PASSWORD --admin_email=admin@mail.cdri"

apache2-foreground
