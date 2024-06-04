# Client machines
To be able to build them, [human-emulation](https://gitlab.ics.muni.cz/ai-dojo/human-emulation) must be present in the `docker` subdirectory.

## Regular workstation

- bash
- human-bot

### Configuration
Create workstation user account

- `USER_NAME=employee`
- `USER_PASSWORD=employee`

Humanbot installation

- `HUMANBOT_WHEEL=humanbot-0.0.0-py3-none-any.whl`

Also, pass other settings for Cryton Worker. Mainly:

- `CRYTON_WORKER_RABBIT_HOST=cryton-rabbit`
- `CRYTON_WORKER_RABBIT_USERNAME=cryton`
- `CRYTON_WORKER_RABBIT_PASSWORD=cryton`
- `CRYTON_WORKER_NAME=client3`

### Build and push
```shell
docker build -t registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:latest --target workstation images/client/
docker push registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:latest
```

## Workstation with active phishing

### Build and push
```shell
docker build -t registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:phished --target phished images/client/
docker push registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:phished
```

## Workstation with a developer account

- bash
- human-bot
- developer-account

### Configuration
Same as the regular workstation.

Create developer account

- `DEVELOPER_USER_NAME=developer`
- `DEVELOPER_USER_PASSWORD=developer`

Remote DB config

- `DATABASE_NAME=cdri`
- `DATABASE_USER=cdri`
- `DATABASE_PASSWORD=cdri`
- `DATABASE_HOST=wordpress_db_node`

### Build and push
```shell
docker build -t registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:developer --target developer images/client/
docker push registry.gitlab.ics.muni.cz:443/ai-dojo/dr-emu/workstation:developer
```

### Troubleshooting
Once you enter the developer account, use `su developer --login` to create clean session without the Docker variables.