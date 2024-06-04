# Web server
WordPress server.

### Configuration
The hostname must be `wordpress_node`.

WordPress website config:

- `WP_HOSTNAME=wordpress_node`
- `WP_ADMIN_NAME=wordpress`
- `WP_ADMIN_PASSWORD=wordpress`

WordPress DB configuration:``

- `WORDPRESS_DB_HOST=wordpress_db_node`
- `WORDPRESS_DB_USER=cdri`
- `WORDPRESS_DB_PASSWORD=cdri`
- `WORDPRESS_DB_NAME=cdri`

### Build and push
```shell
docker build -t registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/web-server:latest images/web-server/
docker push registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/web-server:latest
```

## Possible exploit
Alternative vulnerable version compatible with a vulnerable mysql:
4.8.3-php7.1-apache
