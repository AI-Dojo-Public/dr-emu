#!/bin/bash

cat << EOF > /root/haraka/config/plugins
access
rcpt_to.in_host_list
data.headers
attachment
test_queue
max_unrecognized_commands
EOF

cat << EOF >> /root/haraka/config/host_list
haraka.test
EOF
