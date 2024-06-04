# Haraka server
[Haraka](https://github.com/haraka/Haraka) mail server.

### Configuration
The hostname must be `haraka_node`.

### Build and push
```shell
docker build -t registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/mail-server:latest images/mail-server/
docker push registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/mail-server:latest
```

## exploit
https://www.exploit-db.com/exploits/41162

[//]: # (TODO: The logs, emails, preferably an account name will match the existing testing/developer account.)
