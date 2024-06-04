#!/bin/sh

sed -i "s/line01/Wed Dec  7 16:07:32 2022 [pid 01] CONNECT: Client "$LOGS_USER_ADDRESS"/g" /var/log/vsftpd.log
sed -i "s/line03/Wed Dec  7 16:07:32 2022 [pid 03]: User "$LOGS_USER_NAME" logged in./g" /var/log/vsftpd.log

exec "$@"
