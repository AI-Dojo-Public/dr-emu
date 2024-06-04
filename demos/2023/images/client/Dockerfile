FROM debian:12-slim as client

ENV USER_NAME=employee
ENV USER_PASSWORD=employee
ENV HOME=/home/${USER_NAME}

# Install dependencies
RUN apt update && apt install -y \
    bash \
    curl \
    wget \
    iproute2 \
    openssh-client \
    openssl \
    inetutils-ping \
    python3 \
    python3-venv

# Create workstation user
RUN useradd --password $(openssl passwd -1 $USER_NAME) --shell /bin/bash --user-group --create-home $USER_PASSWORD

FROM client as human_setup

RUN curl -sSL https://install.python-poetry.org | python3 -
RUN ~/.local/bin/poetry config virtualenvs.create false

WORKDIR /human-agent

COPY docker/human-emulation .

RUN python3 -m venv venv
RUN . venv/bin/activate && ~/.local/bin/poetry install

FROM client as worker_setup

WORKDIR /worker

COPY docker/human-emulation/humanbot_cryton_module/mod.py modules/mod_humanbot/mod.py

RUN python3 -m venv venv
RUN . venv/bin/activate && pip install cryton-worker==1.*
RUN . venv/bin/activate && pip install msgspec

FROM client as workstation
USER $USER_NAME
WORKDIR $HOME

COPY --from=worker_setup --chown=$USER_NAME:$USER_NAME --chmod=700 /worker $HOME/.local/cryton-worker
RUN ln -s -f /usr/bin/python3 $HOME/.local/cryton-worker/venv/bin/python

COPY --from=human_setup --chown=$USER_NAME:$USER_NAME --chmod=700 /human-agent /human-agent
RUN ln -s -f /usr/bin/python3 /human-agent/venv/bin/python

COPY --chown=$USER_NAME:$USER_NAME --chmod=777 docker/phishing.py $HOME/phishing.py
COPY --chown=$USER_NAME:$USER_NAME --chmod=700 docker/entrypoint.sh $HOME/entrypoint.sh

ENTRYPOINT [ "/bin/bash", "./entrypoint.sh" ]
CMD [ "tail", "-f", "/dev/null" ]

FROM workstation as phished
CMD [ "python3", "phishing.py" ]

FROM workstation as developer

ENV DEVELOPER_USER_NAME=developer
ENV DEVELOPER_USER_PASSWORD=developer
ENV DEVELOPER_HOME=/home/${DEVELOPER_USER_NAME}/

ENV DATABASE_NAME=cdri
ENV DATABASE_USER=cdri
ENV DATABASE_PASSWORD=cdri
ENV DATABASE_HOST=wordpress_db_node

USER root

# Install dependencies
RUN apt update && apt install -y \
    mariadb-client \
    openssh-server \
    sudo

RUN useradd --password $(openssl passwd -1 $DEVELOPER_USER_PASSWORD) --shell /bin/bash --user-group --create-home --groups sudo $DEVELOPER_USER_NAME

RUN sed -i 's/#PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config
RUN sed -i 's/ChallengeResponseAuthentication no/ChallengeResponseAuthentication yes/g' /etc/ssh/sshd_config

RUN echo "$DEVELOPER_USER_NAME ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER $DEVELOPER_USER_NAME
WORKDIR $DEVELOPER_HOME

COPY --chown=$DEVELOPER_USER_NAME:$DEVELOPER_USER_NAME --chmod=700 docker/developer_entrypoint.sh entrypoint.sh
COPY --chown=$DEVELOPER_USER_NAME:$DEVELOPER_USER_NAME --chmod=600 docker/developer_bash_history .bash_history

RUN ln -s .bash_history .history

CMD [ "tail", "-f", "/dev/null" ]
