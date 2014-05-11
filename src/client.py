
from threading import Timer
from select import select
from sys import exit, stdin
from os import path
import socket
import json

import node
import routing_table


BUFFER = 1024**2
OUTPUT_FILE = 'ouput'

class Client(object):

    def __init__(self, config_file):
        """ Configure the bfclient from the config_file """
        self.ip = '127.0.0.1'
        self.ip = socket.gethostbyname(socket.gethostname())
        self.name = None
        self.port = None
        self.timeout = None
        self.neighbors = dict()
        self.ignore_neighbors = set()
        self.udp = None
        self.routing_table = None
        self.transmit_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.transmit_conn.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,70000)
        self.timeouts = dict()

        self.file_chunk = None
        self.chunk_number = None
        self.num_chunks = 2
        self.recieved_chunks = (0, dict())

        with open(config_file, 'r') as f:
            config = f.readline().strip().split()
            self.port = int(config[0])
            self.timeout = float(config[1])
            if len(config) == 4:
                self.file_chunk = config[2]
                self.chunk_number = config[3]
            if len(config) == 5:
                self.num_chunks[4]

            for line in f:
                ip_port, weight = line.strip().split()
                ip, port = ip_port.split(":")
                name = "{}:{}".format(ip, port)
                self.neighbors[name] = node.Node(ip, int(port), float(weight))
                self.reset_timeout_node(name)
                

        # validation
        if self.file_chunk and not path.isfile(self.file_chunk):
            print 'File chunk, {}, does not exist'.format(self.file_chunk)
            self.shutdown_node()
            exit(1)

        # create routing table
        self.name = "{}:{}".format(self.ip, self.port)
        self.routing_table = routing_table.RoutingTable(
                self.neighbors.values(), node.Node(self.ip, self.port, 0))

        # make socket
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.udp.bind((self.ip, self.port))
        except socket.error, e:
            print e
            self.shutdown_node()

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
            if neighbor.name() not in self.ignore_neighbors:
                neighbor.update_rt(
                        self.routing_table.transmit_str(neighbor.weight),
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
        if node_name not in self.ignore_neighbors:
            self.remove_node(node_name)
            print '{} timed out'.format(node_name)


    def remove_node(self, node_name, ignore=False):
        """ Removes a node from this neighbor """
        # cancel timeout timer
        if node_name in self.timeouts:
            self.timeouts[node_name].cancel()
            del self.timeouts[node_name]
        # remove node from neighbors
        if node_name in self.neighbors:
            del self.neighbors[node_name]
        # remove node from routing table
        self.routing_table.remove_node(node_name)
        # broadcast new routing table
        self.broadcast_rt()
        if ignore:
            self.ignore_neighbors.add(node_name)


    def shutdown_node(self):
        """ Shuts donw the node. Others will let it timeout """
        # cancel timer threads
        if hasattr(self, 'broadcast_timer'):
            self.broadcast_timer.cancel()
        for t in self.timeouts.values():
            t.cancel()
        # close process
        print 'SHUTTING DOWN NODE'
        exit(0)


    def add_node(self, pkt):
        """ add a node, stop an ignore if necessary """
        node_name = pkt['name']
        ip, port = pkt['ip'], pkt['port']
        self.ignore_neighbors.discard(node_name)  # stop ignoring node
        self.neighbors[node_name] = node.Node(ip, port, pkt['weight'])
        if 'data' in pkt:  # regular update
            self.routing_table.update(pkt)
        elif 'weight' in pkt:  # link up
            self.routing_table.add_neighbor(node_name, pkt['weight'])
        self.broadcast_rt()


    def forward_chunk(self, pkt):
        ip, port = self.routing_table.first_step(pkt['destination'])
        if not ip:
            print 'No link to {} fround from {}, canceling transfer of chunk {}'.format(
                pkt['destination'], self.name, pkt['seq_num']
            )
            return

        next_step = '{}:{}'.format(ip, port)
        self.neighbors[next_step].message(
                self.routing_table.transmit_chunk(pkt), self.transmit_conn)
        print 'Forward chunk {} to {}, dest={}'.format(
                pkt['seq_num'], '{}:{}'.format(ip, port), pkt['destination'])

    def forward_get_file(self, pkt):
        ip, port = self.routing_table.first_step(pkt['destination'])
        if not ip or not port:
            print 'No route to {} found'.format(pkt['destination'])
            return
        next_step = '{}:{}'.format(ip, port)
        if next_step == self.name:
            return
        self.neighbors[next_step].message(json.dumps(pkt), self.transmit_conn)


    def broadcast_get_file(self):
        for dest in self.routing_table.reachable_list():
            pkt = self.routing_table.broadcast_transmit_str(dest)
            self.forward_get_file(pkt)
            

    def send_file_chunk(self, ip_addr, port):
        with open(self.file_chunk) as f:
            data = f.read().encode('hex')
        self.forward_chunk(self.routing_table.make_transmit_chunk(
            ip_addr, port, data, self.chunk_number, self.num_chunks))


    def recieve_chunk(self, pkt):
        if not self.recieved_chunks[0]:
            self.recieved_chunks = (pkt['num_chunks'], dict())
        self.recieved_chunks[1][pkt['seq_num']] = pkt['data']
        print 'Recieved chunk #{} from {}'.format(pkt['seq_num'], pkt['name'])
        print 'Steps:'
        print '\n'.join(['{} Step #{} @ {}'.format(dt, i+1, n)
                for i, (n, dt) in enumerate(pkt['steps'])])

        if len(self.recieved_chunks[1]) == self.recieved_chunks[0]:
            print 'Recieved all {} chunks, writing file to {}'.format(
                    self.recieved_chunks[0], OUTPUT_FILE)
            with open(OUTPUT_FILE, 'wb+') as f:
                for i in xrange(1, self.recieved_chunks[0]+1):
                    f.write(self.recieved_chunks[1][str(i)].decode('hex'))
            self.recieved_chunk = (0, dict())


    def process_pkt(self, pkt, ip, port):
        """ Process a packet that is received on the UDP socket """
        node_name = pkt['name']

        # Process update to routing table
        if pkt['type'] == routing_table.RT_UPDATE and node_name not in self.ignore_neighbors:
            self.reset_timeout_node(node_name)
            # if a new neighbor
            if node_name not in self.neighbors:
                self.add_node(pkt)

            self.update_rt(pkt)

        # Stop ignoring a node that has been linked up
        elif pkt['type'] == routing_table.RT_LINKUP:
            self.reset_timeout_node(node_name)
            self.add_node(pkt)
            self.update_rt(pkt)

        # forward or recieve a chunk
        elif pkt['type'] == routing_table.RT_TRANSFER:
            if pkt['destination'] == self.name:
                self.recieve_chunk(pkt)
            else:
                self.forward_chunk(pkt)

        elif pkt['type'] == routing_table.TRANSFER_BROADCAST:
            if self.name == pkt['destination']:
                if self.file_chunk:
                    self.send_file_chunk(pkt['ip'], pkt['port'])
                return
            self.forward_get_file(pkt)


    def process_command(self, command, args):
        """ Process a user inputted command """
        command = command.upper()

        # Remove a link with a neighbor
        if command == 'LINKDOWN':
            if len(args) != 2:
                print 'USUAGE:\n\tLINKDOWN <ip addr> <port>'
                return
            down_node = '{}:{}'.format(args[0], args[1])
            self.remove_node(down_node, ignore=True)

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
            print 'CALLING ADD_NODE() HERE w/ ', up_node
            self.add_node({
                'name': up_node,
                'ip': args[0],
                'port': int(args[1]),
                'weight': weight
            })

        # print out the current routing table
        elif command == 'SHOWRT':
            print 'IGNORING:', self.ignore_neighbors
            print self.routing_table

        # close down the connection
        elif command == 'CLOSE':
            self.shutdown_node()

        # transfer this node's file chunk to a destination
        elif command == 'TRANSFER':
            if len(args) != 2:
                print 'USUAGE:\n\tTRANSFER <ip addr> <port>'
                return
            elif not self.file_chunk or not self.chunk_number:
                print 'There is no file chunk declared for this node'
                print 'please alter the config and restart the node'
                return
            self.send_file_chunk(args[0], int(args[1]))

        # broadcast to have the file sent to this node
        elif command == 'GET':
            if self.file_chunk:
                with open(self.file_chunk, 'rb') as f:
                    data = f.read().encode('hex')
                self.recieve_chunk(self.routing_table.make_transmit_chunk(
                    self.ip,
                    self.port,
                    data,
                    self.chunk_number,
                    self.num_chunks
                ))
                
            self.broadcast_get_file()

        else:
            print 'Command not recognized'

    def run(self):
        """ listen for commands an incoming messages to update the table """
        while True:
            input, _, _ = select([self.udp, stdin], [], [])
            for s in input:
                if s == self.udp:
                    msg, (ip, port) = s.recvfrom(BUFFER)
                    pkt = json.loads(msg)
                    self.process_pkt(pkt, ip, port)
                elif s == stdin:
                    user_input = stdin.readline().strip().split()
                    if len(user_input):
                        command, args = user_input[0], user_input[1:]
                        self.process_command(command, args)
