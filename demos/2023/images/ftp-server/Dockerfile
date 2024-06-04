FROM uexpl0it/vulnerable-packages:backdoored-vsftpd-2.3.4 as production

ENV LOGS_USER_ADDRESS="developer"
ENV LOGS_USER_NAME="developer"

COPY docker/vsftpd.log /var/log/vsftpd.log
COPY docker/entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash", "-c", "/bin/bash run.sh"]
