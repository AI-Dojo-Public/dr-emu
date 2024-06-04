# Database server
MySQL database server.

### Configuration
The hostname must be `wordpress_db_node`.

Setup variables:
`MYSQL_ROOT_PASSWORD=cdri`
`MYSQL_DATABASE=cdri`
`MYSQL_USER=cdri`
`MYSQL_PASSWORD=cdri`

### Build and push
```shell
docker build -t registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/database-server:latest images/database-server/
docker push registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/database-server:latest
```

## Possible exploit
Alternative vulnerable version compatible with a vulnerable WordPress:
https://hub.docker.com/_/mysql/tags?page=1&name=5.7.15
https://packetstormsecurity.com/files/138678/MySQL-5.7.15-5.6.33-5.5.52-Remote-Code-Execution.html
