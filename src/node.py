
import socket

class Node(object):

    def __init__(self, ip, port, weight):
        self.ip = ip
        self.port = port
        self.weight = weight
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def update_rt(self, rt_str):
        self.conn.sendto(rt_str, (self.ip, self.port))

    def name(self):
        return "{}:{}".format(self.ip, self.port)

    def forward_file(self, f, dest):
        pass
