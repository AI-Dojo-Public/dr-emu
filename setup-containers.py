import docker

client = docker.from_env()

gateways = {"vulnerable-ftp": "192.168.92.1", "wordpress-app": "192.168.93.1", "vulnerable-db": "192.168.92.1",
            "vulnerable-user": "192.168.91.1"}
commands = ["apt update -y", "apt install iproute2 -y", "ip route del default"]

for container_name in gateways.keys():
    container = client.containers.get(container_name)
    for command in commands:
        container.exec_run(command)
    container.exec_run(f"ip route add default via {gateways[container_name]}")

print("Done!")
