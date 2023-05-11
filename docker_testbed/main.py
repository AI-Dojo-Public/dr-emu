import asyncio
import time

import docker

from docker_testbed.cyst_parser import CYSTParser
from docker_testbed.controller import Controller


async def main():
    docker_client = docker.from_env()
    parser = CYSTParser(docker_client)

    parser.parse()

    controller = Controller(parser.networks, parser.routers, parser.nodes)

    try:
        await controller.start()
    except Exception as ex:
        await controller.stop(check_id=True)
        raise ex

    while input('Type in "Y" and press ENTER to exit: ').lower() != "y":
        continue

    await controller.stop()


if __name__ == "__main__":
    asyncio.run(main())
