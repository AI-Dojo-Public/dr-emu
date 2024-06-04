FROM ubuntu:16.04 as production

# TODO: https://www.infosecmatter.com/metasploit-module-library/?mm=exploit/linux/smtp/haraka

WORKDIR /

RUN apt update && apt install -y \
    gcc \
    g++ \
    make \
    python \
    git

RUN #ln -s /usr/bin/python2 /usr/bin/python
RUN git clone --single-branch --branch v0.12 https://github.com/nodejs/node.git
RUN git clone --single-branch --branch v2.8.8 https://github.com/haraka/Haraka.git

WORKDIR /node

RUN ./configure
RUN make -j4
RUN ./node -e "console.log('Hello from node.js ' + process.version)"
RUN make install

WORKDIR /Haraka

COPY docker/package.json package.json

RUN npm config set save-exact=true
RUN npm install -g --nodedir=/node

#Haraka setup
RUN haraka -i /root/haraka

COPY docker/haraka.sh /app/haraka.sh
RUN /bin/bash /app/haraka.sh

CMD [ "haraka", "-c", "/root/haraka" ]
