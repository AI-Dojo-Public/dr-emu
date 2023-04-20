import docker

from docker_testbed.cyst_parser import CYSTParser
from docker_testbed.controller import Controller


if __name__ == '__main__':
    docker_client = docker.from_env()
    parser = CYSTParser(docker_client)

    parser.parse()

    controller = Controller(parser.networks, parser.routers, parser.nodes)

    try:
        controller.start()
    except Exception as ex:
        controller.stop(check_id=True)
        raise ex

    while input("Type in \"Y\" and press ENTER to exit: ").lower() != "y":
        continue

    controller.stop()
