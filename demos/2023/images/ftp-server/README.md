# FTP server
Vulnerable version (2.3.4) of vsftpd.

### Configuration
The hostname must be `vsftpd_node`.

Update the logs for the developer user login

- `LOGS_USER_ADDRESS="developer"`
- `LOGS_USER_NAME="developer"`

### Build and push
```shell
docker build -t registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/ftp-server:latest images/ftp-server/
docker push registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/ftp-server:latest
```

## exploit
https://www.infosecmatter.com/metasploit-module-library/?mm=exploit/unix/ftp/vsftpd_234_backdoor
https://github.com/Anon-Exploiter/vulnerable-packages/blob/master/backdoored-vsftpd-2.3.4/Dockerfile

[//]: # (TODO: The logs, folder, preferably an account name will match the existing testing/developer account.)
