
import json

RT_UPDATE = "ROUTE_UPDATE"
RT_LINKUP = "ROUTE_LINKUP"
RT_LINKDOWN = "ROUTE_LINKDOWN"

class RoutingTable(object):

    def __init__(self, src_node, neighbor_list, source):
        self.table = {} # from --> to --> [cost, first step]
        self.src_node = src_node

        # initialize table for every node
        self.table[self.src_node] = {}
        for neighbor in neighbor_list:
            self.table[neighbor.name()] = {}

        # initalize all values to inf for nodes
        for neighbor in neighbor_list + [source]:
            from_node = neighbor.name()
            for to_node in neighbor_list + [source]:
                self.table[from_node][to_node.name()] = [float('inf'), 'N/A']
            self.table[from_node][from_node] = [0, from_node]

        # set known neighbor values
        for neighbor in neighbor_list + [source]:
            self.table[self.src_node][neighbor.name()] = [neighbor.weight,
                                                          self.src_node]


    def update(self, packet):
        # see transmit_str() for format
        neighbor_name = packet['name']
        neighbor_vector = packet['data']
        self.table[neighbor_name] = neighbor_vector

        update = False

        # check if there's a new connection
        if (neighbor_name not in self.table[self.src_node] and
                self.src_node in neighbor_vector):
            self.table[self.src_node][neighbor_name] = (
                [neighbor_vector[self.src_node][0], self.src_node])
            update = True

        # update if link with neighbor cost is now cheaper
        if neighbor_vector[self.src_node][0] < self.table[self.src_node][neighbor_name][0]:
            self.table[self.src_node][neighbor_name] = (
                    [neighbor_vector[self.src_node][0], self.src_node])
            update = True

        return update or self.__recompute()


    def __recompute(self):
        """ Re-calculates everything, returns True if changes are made """
        changes = False
        # iterate through all neigboring nodes of the src node
        for dest, cost in self.table[self.src_node].iteritems():
            # find all possible costs
            possible_costs = []
            for n_name, n_cost in self.table[self.src_node].iteritems():
                possible_costs.append([n_cost[0] + self.table[n_name][dest][0],
                                       n_name])
            # assign the smallest one
            self.table[self.src_node][dest] = min(*possible_costs)
            if self.table[self.src_node][dest] != cost:
                changes = True

        return changes


    def link_down(self, node_name):
        """ Takes down a link and returns the pkt string """
        # if the node exists and isn't already INF
        if (node_name in self.table[self.src_node] and
                self.table[self.src_node][node_name] != [float('inf'), 'N/A']):
            self.table[self.src_node][node_name] = [float('inf'), 'N/A']
            print 'Removed link to {}'.format(node_name)
            return self.transmit_linkdown(node_name)
        return None


    def transmit_linkdown(self, node_name):
        return json.dumps({
            "type": RT_LINKDOWN,
            "name": self.src_node,
            "data": {
                # transmit our own name since we want the recieving node to
                # ignore the transmitted 
                "name": self.src_node  
            }
        })


    def link_up(self, node_name, weight):
        """ Adds to routing table, returns True if changes are made """
        if node_name in self.table[self.src_node]:
            if self.table[self.src_node][node_name] == [weight, self.src_node]:
                return False

        self.table[self.src_node][node_name] = [weight, self.src_node]
        return True


    def transmit_linkup(self, n):
        return json.dumps({
            "type": RT_LINKUP,
            "name": self.src_node,
            "data": {
                "name": n.name,
                "ip": n.ip,
                "port": n.port,
                "weight": n.weight
            }
        })


    def transmit_str(self):
        return json.dumps({
            "type": RT_UPDATE,
            "name": self.src_node,
            "data": self.table[self.src_node]
        })


    def __str__(self):
        rt = ""
        for client, (cost, first_step) in self.table[self.src_node].iteritems():
            rt += "Destination = {}, Cost = {}, Link = ({})\n".format(
                    client, cost, first_step)
        return rt
