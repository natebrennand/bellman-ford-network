
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
        self.neighbors = dict()
        self.udp = None
        self.routing_table = None
        self.transmit_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

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
                name = "{}:{}".format(ip, port)
                self.neighbors[name] = node.Node(ip, int(port), float(weight))
                

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
                self.name, self.neighbors.values(), node.Node(self.ip,
                                                              self.port, 0))
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
        for neighbor in self.neighbors.values():
            neighbor.update_rt(self.routing_table.transmit_str(),
                               self.transmit_conn)
        self.reset_broadcast()


    def update_rt(self, packet):
        """ called with an incoming packet that has a new distance vector """
        if self.routing_table.update(packet):
            # broadcast if change
            self.reset_broadcast()


    def reset_timeout_node(self, node_name):
        """ Reset the timer to remove a neighboring node """
        if node_name in self.timeouts:
            self.timeouts[node_name].cancel()
        self.timeouts[node_name] = Timer(self.timeout*3, self.timeout_node,
                                         args=[node_name])
        self.timeouts[node_name].start()


    def timeout_node(self, node_name):
        """ Remove a node that hasn't been active in 3 * timeout """
        self.remove_node(node_name)
        print '{} timed out'.format(node_name)


    def remove_node(self, node_name):
        """ Removes a node from this neighbor and informs the node that the
            connection is down
        """
        # remove from routing table and notify node
        msg = self.routing_table.link_down(node_name)
        if msg:
            self.neighbors[node_name].message(msg, self.transmit_conn)
        # cancel timeout timer
        self.timeouts[node_name].cancel()
        del self.timeouts[node_name]
        # don't message node
        self.neighbors[node_name].ignore = True
        # broadcast new routing table
        self.broadcast_rt()


    def shutdown_node(self):
        close_msg = self.routing_table.transmit_linkdown(self.name)
        for neighbor in self.neighbors.values():
            neighbor.message(close_msg, self.transmit_conn)
        self.broadcast_timer.cancel()
        for t in self.timeouts.values():
            t.cancel()
        print 'SHUTTING DOWN NODE'
        exit(0)


    def add_node(self, node_name, pkt_data):
        """ stop ignoring a node and add it if necessary """
        update = False
        if self.neighbors[node_name].ignore:
            self.neighbors[node_name].ignore = False
            update = True
        if node_name not in self.neighbors:
            self.neighbors[node_name] = node.Node(pkt_data['ip'],
                                                    pkt_data['port'],
                                                    pkt_data['weight'])
            update = True
        if update:
            self.broadcast_rt()


    def process_pkt(self, pkt):
        """ Process a packet that is received on the UDP socket """
        node_name = pkt['name']
        self.reset_timeout_node(node_name)

        print pkt['type']
        print pkt['data']

        # Process update to routing table
        if pkt['type'] == routing_table.RT_UPDATE:
            if not self.neighbors[pkt['name']].ignore:
                self.update_rt(pkt)
                self.add_node(pkt['name'], pkt['data'])

        # Turn off a link and ignore node
        elif pkt['type'] == routing_table.RT_LINKDOWN:
            down_node = pkt['data']['name']
            self.routing_table.link_down(down_node)
            self.neighbors[down_node].ignore = True

        # Stop ignoring a node that has been linked up
        elif pkt['type'] == routing_table.RT_LINKUP:
            self.add_node(pkt['name'], pkt['data'])



    def process_command(self, command, args):
        """ Process a user inputted command """
        command = command.upper()

        # Remove a link with a neighbor
        if command == 'LINKDOWN':
            if len(args) != 2:
                print 'USUAGE:\n\tLINKDOWN <ip addr> <port>'
                return
            down_node = '{}:{}'.format(args[0], args[1])
            self.remove_node(down_node)

        # add a link to a neighbor and broadcast it
        elif command == 'LINKUP':
            if len(args) != 3:
                print 'USUAGE:\n\tLINKUP <ip addr> <port> <weight>'
                return
            up_node = '{}:{}'.format(args[0], args[1])
            try:
                weight = float(args[2])
            except ValueError:
                print 'USUAGE:\n\tLINKUP <ip addr> <port> <weight>'
                print '<weight> must be a number'
                return
            if self.routing_table.link_up(up_node, weight):
                self.broadcast_rt()

        # print out the current routing table
        elif command == 'SHOWRT':
            print self.routing_table

        # close down the connection
        elif command == 'CLOSE':
            self.shutdown_node()

        elif command == 'TRANSFER':
            pass
        else:
            print 'Command not recognized'

    def run(self):
        """ listen for commands an incoming messages to update the table """
        while True:
            input, _, _ = select([self.udp, stdin], [], [], 2)
            for s in input:
                if s == self.udp:
                    msg, (ip, port) = s.recvfrom(BUFFER)
                    pkt = json.loads(msg)
                    self.process_pkt(pkt)
                elif s == stdin:
                    user_input = stdin.readline().strip().split()
                    if len(user_input):
                        command, args = user_input[0], user_input[1:]
                        self.process_command(command, args)
