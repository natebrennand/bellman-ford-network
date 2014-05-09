
from threading import Timer
from select import select
from sys import exit, stdin
from os import path
import socket
import json

import node
import routing_table


BUFFER = 1024

class Client(object):

    def __init__(self, config_file):
        """ Configure the bfclient from the config_file """
        self.ip = socket.gethostbyname(socket.gethostname())
        self.ip = '127.0.0.1'
        self.name = None
        self.port = None
        self.timeout = None
        self.file_chunk = None
        self.chunk_number = None
        self.neighbors = []
        self.udp = None
        self.routing_table = None

        with open(config_file, 'r') as f:
            config = f.readline().strip().split()
            self.port = int(config[0])
            self.timeout = float(config[1])
            if len(config) == 4:
                self.file_chunk = config[2]
                self.chunk_number = config[3]

            for line in f:
                ip_port, weight = line.strip().split()
                ip, port = ip_port.split(":")
                self.neighbors.append(node.Node(ip, int(port), float(weight)))
                

        # validation
        if self.file_chunk and not path.isfile(self.file_chunk):
            print 'File chunk, {}, does not exist'.format(self.file_chunk)
            exit(1)
        if not len(self.neighbors):
            print 'There must be more than 0 neighboring nodes on startup'
            exit(1)

        # create routing table
        self.name = "{}:{}".format(self.ip, self.port)
        self.routing_table = routing_table.RoutingTable(
                self.name, self.neighbors, node.Node(self.ip, self.port, 0))
        self.timeouts = dict()

        # make socket
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.bind((self.ip, self.port))

        # start broadcast timer
        self.broadcast_rt()

    def reset_broadcast(self):
        """ Resests the timer on the broadcast """
        if hasattr(self, 'broadcast_timer'):
            self.broadcast_timer.cancel()
        self.broadcast_timer = Timer(self.timeout, self.broadcast_rt)
        self.broadcast_timer.start()

    def broadcast_rt(self):
        """ Broadcasts the distance vector to all neighbors """
        for neighbor in self.neighbors:
            neighbor.update_rt(self.routing_table.transmit_str())
        self.reset_broadcast()

    def update_rt(self, packet):
        """ called with an incoming packet that has a new distance vector """
        if self.routing_table.update(packet):
            self.reset_broadcast()

    def reset_timeout_node(self, node_name):
        if node_name in self.timeouts:
            self.timeouts[node_name].cancel()
        self.timeouts[node_name] = Timer(self.timeout*3, self.timeout_node,
                                         args=[node_name])
        self.timeouts[node_name].start()

    def timeout_node(self, node_name):
        self.routing_table.link_down(node_name)
        del self.timeouts[node_name]
        self.broadcast_rt()
        print '{} timed out'.format(node_name)

    def process_pkt(self, pkt):
        node_name = pkt['name']
        self.reset_timeout_node(node_name)

        if pkt['type'] == routing_table.RT_UPDATE:
            if self.update_rt(pkt):
                # rebroadcast if values change
                self.broadcast_rt()

    def run(self):
        """ listen for commands an incoming messages to update the table """
        while True:
            input, _, _ = select([self.udp, stdin], [], [], 2)
            for s in input:
                if s == self.udp:
                    msg, (ip, port) = s.recvfrom(BUFFER)
                    pkt = json.loads(msg)
                    self.process_pkt(pkt)
