
import json
from datetime import datetime

RT_UPDATE = "ROUTE_UPDATE"
RT_LINKUP = "ROUTE_LINKUP"
RT_LINKDOWN = "ROUTE_LINKDOWN"
RT_TRANSFER = "CHUNK_TRANSFER"
TRANSFER_BROADCAST = "TRANSFER_BROADCAST"

DT_FORMAT = "%m/%d/%Y %H:%M:%S.%f"

def get_current_timestamp():
    return datetime.now().strftime(DT_FORMAT)


class RoutingTable(object):

    def __init__(self,neighbor_list, source):
        self.table = {} # from --> to --> [cost, first step]
        self.src_node = source.name()
        self.ip = source.ip
        self.port = source.port
        self.own_edges = dict()

        # add own edges
        self.own_edges = dict((n.name(), [n.weight, self.src_node]) for n in neighbor_list)
        self.own_edges[self.src_node] = [0, self.src_node]

        # initialize table for every node
        self.table[self.src_node] = {}
        for neighbor in neighbor_list:
            self.table[neighbor.name()] = {}

        # initalize all values to inf for nodes
        for neighbor in neighbor_list + [source]:
            from_node = neighbor.name()
            self.table[from_node] = {}
            # for to_node in neighbor_list + [source]:
            #    self.table[from_node][to_node.name()] = [float('inf'), 'N/A']
            self.table[from_node][from_node] = [0, from_node]

        # set known neighbor values
        for neighbor in neighbor_list + [source]:
            self.table[self.src_node][neighbor.name()] = [neighbor.weight,
                                                          self.src_node]


    def add_neighbor(self, node_name, weight):
        self.own_edges[node_name] = [weight, self.src_node]
        self.table[self.src_node][node_name] = [weight, self.src_node]

    
    def reachable_list(self):
        return [dest for dest in self.table[self.src_node].keys()]


    def first_step(self, dest):
        if dest in self.table[self.src_node]:
            step =  self.table[self.src_node][dest][1]
            if step == self.src_node:
                step = dest
            ip, port = step.split(':')
            return ip, int(port)
        return None, None


    def update(self, packet):
        """ Uopdate neighboring node; makes adjacent edge adjustments """
        # see transmit_str() for format of packet
        p_name = packet['name']
        self.table[p_name] = packet['data']
        src_vector = self.table[self.src_node]
        p_vector = self.table[p_name]
        update = False

        # check if there's a new connection to this node
        if p_name not in self.own_edges and self.src_node in p_vector:
            print 'New connection to {}'.format(p_name)
            # add edge to this node's vector
            src_vector[p_name] = [p_vector[self.src_node][0], self.src_node]
            self.own_edges[p_name] = [p_vector[self.src_node][0], self.src_node]
            update = True

        # check if a cheaper connection exists
        elif self.src_node in p_vector and p_name in src_vector:
            other_cost = p_vector[self.src_node]
            our_cost = src_vector[p_name]
            if (other_cost[0] < our_cost[0] and  # cheaper
                    other_cost[1] == p_name):  # direct
                src_vector[p_name] = [other_cost[0], self.src_node]
                update = True

        return update or self.__recompute()


    def remove_node(self, node_name):
        """ Remove all links directly from this node to node_name"""
        # in set of own edges
        if node_name in self.own_edges:
            del self.own_edges[node_name]
        else:
            return

        # if has a set of edges
        del self.table[node_name]

        # first step in path to node
        for dest, (cost, first_step) in self.table[self.src_node].items():
            if first_step == node_name:
                del self.table[self.src_node][dest]

        # delete if last step in path uses connection
        if node_name in self.table[self.src_node]:
            values = self.table[self.src_node][node_name]
            for src in self.table:
                for dest, cost_step in self.table[src].items():
                    if dest == node_name and cost_step == values:
                        del self.table[src][dest]
        
        return True or self.__recompute()


    def __recompute(self):
        """ Re-calculates everything, returns True if changes are made """
        changes = False
        new_table_vector = dict()

        # all nodes with a direct connection or connection from a neighbor
        destinations = set()
        for k in self.own_edges.keys():
            destinations.add(k)
        for k, vector in self.table.items():
            if k != self.src_node:
                for d in vector.keys():
                    destinations.add(d)

        # viable first steps
        first_steps = self.own_edges.items()

        # find the cheapest path to all these nodes
        # A --> B --> C --> D / Dest
        for dest in destinations:
            current_cost = self.table[self.src_node].get(dest, [None, None])
            possible_costs = []
            # loop possible first steps
            # start with A, eventually to B, then C
            for B, (cost1, A) in first_steps:
                if B == dest:
                    possible_costs.append([cost1, A])
                    continue
                # loop looking for second steps
                for D, (cost2, C) in self.table[B].iteritems():
                    # if right destination & doesn't end with 0 steps & doesn't stat w/ 0 steps
                    if D == dest and C != D and A != B:
                        if self.src_node != C: # prevent looping
                            possible_costs.append([cost1 + cost2, B])

            # skip if no options
            if not possible_costs:  
                continue
            # assign the smallest one
            likely_min = min(possible_costs)
            # ignore if current_cost unchanged
            if likely_min[0] != current_cost[0]:
                new_table_vector[dest] = likely_min
                changes = True
            else:
                new_table_vector[dest] = current_cost

        # if size of vector is different
        if len(new_table_vector) != len(self.table[self.src_node]):
            changes = True

        self.table[self.src_node] = new_table_vector
        return changes


    def linkup_str(self, dest_weight):
        """ Broadcast message for RT_UPDATE """
        return json.dumps({
            "type": RT_LINKUP,
            "name": self.src_node,
            "ip": self.ip,
            "port": self.port,
            "weight": dest_weight,
            "data": self.table[self.src_node]
        })


    def transmit_str(self, dest_weight):
        """ Broadcast message for RT_UPDATE """
        return json.dumps({
            "type": RT_UPDATE,
            "name": self.src_node,
            "weight": dest_weight,
            "ip": self.ip,
            "port": self.port,
            "data": self.table[self.src_node]
        })


    def broadcast_transmit_str(self, dest):
        return {
            "type": TRANSFER_BROADCAST,
            "name": self.src_node,
            "destination": dest,
            "ip": self.ip,
            "port": self.port
        }


    def make_transmit_chunk(self,dest_ip, dest_port, data, seq, num):
        # will make the initial packet
        destination = "{}:{}".format(dest_ip, dest_port)
        packet = {
            "type": RT_TRANSFER,
            "name": self.src_node,
            "destination": destination,
            "dest_ip": dest_ip,
            "dest_port": dest_port,
            "data": data,
            "seq_num": seq,
            "num_chunks": num,
            "steps": []
        }
        return packet


    def transmit_chunk(self, packet):
        packet['steps'].append([self.src_node, get_current_timestamp()])
        return json.dumps(packet)


    def __str__(self):
        rt = ""
        for client, (cost, first_step) in self.table[self.src_node].iteritems():
            rt += "Destination = {}, Cost = {}, Link = ({})\n".format(
                    client, cost, first_step)
        return rt
