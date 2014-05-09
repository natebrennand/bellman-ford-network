
from sys import argv, exit
from os import path
import socket

import node



class Client(object):

    def __init__(self, config_file):
        """ Configure the bfclient from the config_file """
        self.ip = socket.gethostbyname(socket.gethostname())
        self.port = None
        self.timeout = None
        self.file_chunk = None
        self.chunk_number = None
        self.neighbors = []
        self.udp = None

        with open(config_file, 'r') as f:
            config = f.readline().strip().split()
            self.port = int(config[0])
            self.timeout = config[1]
            if len(config) == 4:
                self.file_chunk = config[2]
                self.chunk_number = config[3]

            for line in f:
                ip_port, weight = line.strip().split()
                ip, port = ip_port.split(":")
                self.neighbors.append(node.Node(ip, int(port), weight))

        # validation
        if self.file_chunk and not path.isfile(self.file_chunk):
            print 'File chunk, {}, does not exist'.format(self.file_chunk)
            exit(1)
        if not len(self.neighbors):
            print 'There must be more than 0 neighboring nodes on startup'
            exit(1)

        # make socket
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind((self.ip, self.port))


if __name__ == '__main__':
    if len(argv) != 2:
        print 'USAGE: python bfclient.py <config file>'
        exit(1)
    c = Client(argv[1])
